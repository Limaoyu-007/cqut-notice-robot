import json
import logging
import re

import requests

from config import FEISHU_WEBHOOK_URL
from models import AIAnalysis, Notice


logger = logging.getLogger("notice_robot")


def _take_text_chunk(text: str, max_chars: int) -> tuple[str, str]:
    if len(text) <= max_chars:
        return text, ""

    split_at = text.rfind("\n", 0, max_chars + 1)
    if split_at <= 0:
        split_at = max_chars

    return text[:split_at].rstrip(), text[split_at:].lstrip()


def _label_level(value: str) -> str:
    labels = {
        "high": "高",
        "medium": "中",
        "low": "低",
    }
    return labels.get(value, value)


def _numbered_lines(items: list[str], fallback: str) -> str:
    clean_items = [item.strip() for item in items if item and item.strip()]
    if not clean_items:
        clean_items = [fallback]
    return "\n".join(f"{index}. {item}" for index, item in enumerate(clean_items, start=1))


def _content_to_points(content: str | None) -> list[str]:
    if not content:
        return []

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[:5]

    text = re.sub(r"\s+", " ", content).strip()
    if not text:
        return []
    return [text[:260]]


def _format_attachments(notice: Notice) -> str:
    if not notice.attachments:
        return ""

    attachment_lines = [
        f"{index}. {_clean_attachment_name(attachment.name)}\n   {attachment.url}"
        for index, attachment in enumerate(notice.attachments, start=1)
    ]
    return "\n\n📎 附件：\n" + "\n".join(attachment_lines)


def _clean_attachment_name(name: str) -> str:
    return re.sub(r"^\d+[.、]?\s*", "", name)


def _format_ai_card(notice: Notice, analysis: AIAnalysis) -> str:
    title = analysis.clean_title or notice.title
    publish_time = analysis.clean_publish_time or notice.publish_time or "未明确"
    deadline = analysis.deadline or "未明确"
    activity_time = analysis.activity_time or "未明确"
    reason = analysis.reason or analysis.value_for_user or "AI 未给出明确理由，建议结合原文判断。"
    recommended_action = analysis.recommended_action or analysis.action_required or "查看原文确认完整要求。"
    key_points = _numbered_lines(analysis.key_points, "打开原文核对对象、时间、材料和附件要求。")
    main_points = _numbered_lines(
        analysis.main_points or _content_to_points(analysis.clean_content),
        "AI 未能提取明确主要内容，请查看原文。",
    )

    return "\n".join(
        [
            f"📢 【{_label_level(analysis.importance)}重要】{title}",
            "",
            "🧠 AI 解读",
            f"相关度：{analysis.personal_relevance}/100",
            f"为什么值得看：{reason}",
            f"推荐处理：{recommended_action}",
            "",
            "🎯 重点关注",
            key_points,
            "",
            "📌 主要内容",
            main_points,
            "",
            "⏰ 关键时间",
            f"发布时间：{publish_time}",
            f"截止时间：{deadline}",
            f"活动/提交时间：{activity_time}",
            "",
            "✅ 行动建议",
            recommended_action,
            _format_attachments(notice),
            "",
            "🔗 原文链接",
            notice.url,
        ]
    )


def _format_original_notice(notice: Notice) -> str:
    content = notice.content or "未能提取到正文，请查看原文链接。"
    attachments = _format_attachments(notice)
    return "\n".join(
        [
            "📢 官方原文",
            f"标题：{notice.title}",
            "",
            f"发布时间：{notice.publish_time or '未知'}",
            f"发布部门：{notice.department or '未知'}",
            "",
            "正文：",
            content,
            attachments,
            "",
            "🔗 原文链接：",
            notice.url,
        ]
    )


def format_notice_messages(notice: Notice, max_chars: int = 3500) -> list[str]:
    full_message = (
        _format_ai_card(notice, notice.ai_analysis)
        if notice.ai_analysis
        else _format_original_notice(notice)
    )
    if len(full_message) <= max_chars:
        return [full_message]

    messages = []
    remaining = full_message
    while remaining:
        chunk, remaining = _take_text_chunk(remaining, max_chars)
        messages.append(chunk)
    return messages


def send_feishu_message(notice: Notice) -> bool:
    if not FEISHU_WEBHOOK_URL or "xxxxxxxx" in FEISHU_WEBHOOK_URL:
        logger.warning("Feishu webhook is not configured; skipped sending.")
        return False

    headers = {"Content-Type": "application/json"}

    try:
        for message in format_notice_messages(notice):
            payload = {
                "msg_type": "text",
                "content": {"text": message},
            }
            response = requests.post(FEISHU_WEBHOOK_URL, headers=headers, data=json.dumps(payload), timeout=10)
            if response.status_code != 200:
                logger.error("Feishu request failed, status=%s", response.status_code)
                return False
            result = response.json()
            if result.get("code") != 0:
                logger.error("Feishu send failed: %s", result.get("msg"))
                return False
        logger.info("Feishu message sent: %s", notice.title)
        return True
    except Exception as e:
        logger.exception("Feishu send exception: %s", e)

    return False
