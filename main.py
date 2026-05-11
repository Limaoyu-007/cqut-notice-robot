import argparse
import json
import logging
import os
import time
from dataclasses import asdict
from datetime import date

import schedule

from ai_analyzer import analyze_notice
from config import (
    AI_API_BASE_URL,
    AI_API_KEY,
    AI_ENABLED,
    AI_MODEL,
    BROWSER_PATH,
    DRY_RUN,
    ERROR_ALERT_ENABLED,
    LOG_PATH,
    NOTICE_LIST_URLS,
    REQUEST_TIMEOUT,
    SCHEDULE_INTERVAL_MINUTES,
    USER_AGENT,
    USER_PROFILE,
)
from crawler import NoticeCrawler
from daily_digest import format_daily_digest
from db import DBManager
from error_notifier import notify_error
from keyword_classifier import classify_notice_by_keywords
from logger_setup import setup_logging
from notifier import format_notice_messages, send_feishu_message, send_feishu_text
from parser import parse_notice_detail_info, parse_notices
from push_policy import DeliveryStyle, decide_delivery_style


logger = logging.getLogger("notice_robot")


def save_html(html: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("HTML saved to: %s", path)


def save_notices(notices, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = [asdict(notice) for notice in notices]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Notices exported to: %s", path)


def preview_notice(notice) -> None:
    messages = format_notice_messages(notice)
    for index, message in enumerate(messages, start=1):
        print(f"\n====== DRY RUN message preview {index}/{len(messages)} ======")
        print(message)


def collect_notices_from_sources(list_urls, fetch_html_func):
    notices = []
    seen_urls = set()

    for list_url in list_urls:
        html = fetch_html_func(list_url)
        if not html:
            logger.warning("Failed to fetch notice list: %s", list_url)
            continue

        source_notices = parse_notices(html, list_url)
        logger.info("Parsed %s notices from %s.", len(source_notices), list_url)

        for notice in source_notices:
            if notice.url in seen_urls:
                continue
            seen_urls.add(notice.url)
            notices.append(notice)

    return notices


def _analyze_notice_with_config(notice):
    return analyze_notice(
        notice,
        api_key=AI_API_KEY,
        user_profile=USER_PROFILE,
        api_base_url=AI_API_BASE_URL,
        model=AI_MODEL,
    )


def attach_ai_analysis(notice, db, analyze_func, ai_enabled: bool = True) -> None:
    if ai_enabled:
        cached_notice = db.get_by_url(notice.url)
        if cached_notice and cached_notice.ai_analysis:
            notice.ai_analysis = cached_notice.ai_analysis
            logger.info("Reused cached AI analysis: %s", notice.title)
            return

        notice.ai_analysis = analyze_func(notice)

    if not notice.ai_analysis:
        notice.ai_analysis = classify_notice_by_keywords(notice)
        if notice.ai_analysis:
            logger.info("Applied keyword fallback analysis: %s", notice.title)


def deliver_notice(
    notice,
    dry_run: bool = False,
    delivery_style: DeliveryStyle | None = None,
    send_func=send_feishu_message,
    preview_func=preview_notice,
) -> bool:
    selected_style = delivery_style or decide_delivery_style(notice)

    if selected_style == DeliveryStyle.DIGEST_ONLY:
        logger.info("Notice stored for digest only: %s", notice.title)
        return True

    if dry_run:
        preview_func(notice)
        return True

    style_arg = None
    if selected_style == DeliveryStyle.BRIEF:
        style_arg = "brief"
    elif selected_style == DeliveryStyle.DETAILED:
        style_arg = "detailed"

    ok = send_func(notice, style=style_arg)
    if not ok:
        logger.error("Notice delivery failed: %s", notice.title)
    return ok


def hydrate_notice_detail(notice, crawler) -> None:
    detail_html = crawler.fetch_html(url=notice.url, timeout=REQUEST_TIMEOUT)
    if not detail_html:
        logger.warning("Failed to fetch notice detail: %s", notice.url)
        notice.content = "获取详情失败"
        return

    detail = parse_notice_detail_info(detail_html, notice.url)
    if detail.title:
        notice.title = detail.title
    if detail.publish_time:
        notice.publish_time = detail.publish_time
    notice.content = detail.content
    notice.attachments = detail.attachments


def resolve_dry_run(cli_dry_run: bool, env_dry_run: bool = DRY_RUN) -> bool:
    return cli_dry_run or env_dry_run


def job(dry_run: bool = False):
    logger.info("Start crawling notices. dry_run=%s", dry_run)

    db = DBManager("data/notices.db")
    crawler = NoticeCrawler(user_agent=USER_AGENT, browser_path=BROWSER_PATH)

    try:
        notices = collect_notices_from_sources(
            NOTICE_LIST_URLS,
            lambda url: crawler.fetch_html(url=url, timeout=REQUEST_TIMEOUT),
        )
        if not notices:
            raise RuntimeError("列表页抓取失败或没有解析到通知")
        logger.info("Parsed %s notices from %s sources.", len(notices), len(NOTICE_LIST_URLS))

        new_count = 0
        for index, notice in enumerate(notices, start=1):
            if db.exists(notice.url):
                logger.info("[%s/%s] Exists, skipped: %s", index, len(notices), notice.title)
                continue

            new_count += 1
            logger.info("[%s/%s] Fetching detail: %s", index, len(notices), notice.title)
            hydrate_notice_detail(notice, crawler)
            attach_ai_analysis(notice, db, _analyze_notice_with_config, AI_ENABLED)
            delivery_style = decide_delivery_style(notice)

            if not dry_run:
                db.insert(notice)

            if not deliver_notice(notice, dry_run=dry_run, delivery_style=delivery_style) and ERROR_ALERT_ENABLED:
                notify_error("飞书推送", f"通知推送失败：{notice.title}", dry_run=dry_run)

            logger.info("Notice processed. time=%s url=%s", notice.publish_time, notice.url)

        logger.info("Crawl finished. New notices: %s", new_count)

        if not dry_run:
            save_notices(db.get_all(), "data/notices.json")
    except Exception as e:
        logger.exception("Job failed: %s", e)
        if ERROR_ALERT_ENABLED:
            notify_error("整轮任务", e, dry_run=dry_run)
    finally:
        crawler.close()
        db.close()


def send_daily_digest(
    date_text: str | None = None,
    db_factory=DBManager,
    send_text_func=send_feishu_text,
) -> bool:
    selected_date = date_text or date.today().isoformat()
    db = db_factory("data/notices.db")
    try:
        notices = db.get_by_publish_date(selected_date)
        message = format_daily_digest(notices, selected_date)
        return send_text_func(message)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="CQUT notice robot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preview messages without sending Feishu notifications or writing new notices",
    )
    args = parser.parse_args()
    dry_run = resolve_dry_run(args.dry_run)

    setup_logging(LOG_PATH)
    logger.info("Start scheduled task, every %s minutes.", SCHEDULE_INTERVAL_MINUTES)
    job(dry_run=dry_run)

    if dry_run:
        return

    schedule.every(SCHEDULE_INTERVAL_MINUTES).minutes.do(job)
    schedule.every().day.at("22:00").do(send_daily_digest)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
