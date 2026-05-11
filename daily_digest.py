from collections import defaultdict

from models import Notice


IMPORTANCE_LABELS = {
    "high": "高重要",
    "medium": "中重要",
    "low": "低重要",
}


def _notice_importance(notice: Notice) -> str:
    if notice.ai_analysis:
        return notice.ai_analysis.importance
    return "medium"


def _notice_action(notice: Notice) -> str:
    if notice.ai_analysis:
        return notice.ai_analysis.recommended_action or notice.ai_analysis.action_required or "查看原文确认完整要求。"
    return "查看原文确认完整要求。"


def format_daily_digest(notices: list[Notice], date_text: str) -> str:
    lines = [f"📬 {date_text} 通知摘要", ""]
    if not notices:
        lines.append("今天没有记录到新通知。")
        return "\n".join(lines)

    groups: dict[str, list[Notice]] = defaultdict(list)
    for notice in notices:
        groups[_notice_importance(notice)].append(notice)

    for importance in ["high", "medium", "low"]:
        group = groups.get(importance, [])
        if not group:
            continue

        lines.append(f"{IMPORTANCE_LABELS[importance]} {len(group)} 条")
        for index, notice in enumerate(group, start=1):
            lines.append(f"{index}. {notice.title}")
            lines.append(f"   建议：{_notice_action(notice)}")
            lines.append(f"   原文：{notice.url}")
        lines.append("")

    return "\n".join(lines).rstrip()
