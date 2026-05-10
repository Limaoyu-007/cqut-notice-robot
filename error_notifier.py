import logging
import time
from typing import Callable

import requests

from config import FEISHU_WEBHOOK_URL


def format_error_message(stage: str, error: Exception | str) -> str:
    return "\n".join(
        [
            "⚠️ 通知机器人异常",
            f"阶段：{stage}",
            f"时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"错误：{error}",
        ]
    )


def send_error_message(message: str) -> bool:
    if not FEISHU_WEBHOOK_URL or "xxxxxxxx" in FEISHU_WEBHOOK_URL:
        return False

    payload = {
        "msg_type": "text",
        "content": {"text": message},
    }
    response = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
    if response.status_code != 200:
        return False
    result = response.json()
    return result.get("code") == 0


def notify_error(
    stage: str,
    error: Exception | str,
    dry_run: bool = False,
    send_func: Callable[[str], bool] = send_error_message,
    logger: logging.Logger | None = None,
) -> bool:
    message = format_error_message(stage, error)
    active_logger = logger or logging.getLogger("notice_robot")
    active_logger.error(message)

    if dry_run:
        return False

    try:
        return send_func(message)
    except Exception as exc:
        active_logger.error("错误通知发送失败：%s", exc)
        return False
