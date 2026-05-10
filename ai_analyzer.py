import json
import logging
from typing import Any, Callable

import requests

from models import AIAnalysis, Notice


logger = logging.getLogger("notice_robot")
DEFAULT_API_BASE_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value.lower() in allowed:
        return value.lower()
    return default


def _normalize_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def parse_ai_analysis(content: str) -> AIAnalysis:
    data = json.loads(content)
    normalized = {
        "importance": _normalize_choice(data.get("importance"), {"high", "medium", "low"}, "medium"),
        "personal_relevance": _normalize_score(data.get("personal_relevance")),
        "clean_title": data.get("clean_title") or None,
        "clean_publish_time": data.get("clean_publish_time") or None,
        "clean_content": data.get("clean_content") or None,
        "category": str(data.get("category") or "未分类"),
        "deadline": data.get("deadline") or None,
        "action_required": str(data.get("action_required") or "查看原文"),
        "target_audience": _as_list(data.get("target_audience")),
        "key_points": _as_list(data.get("key_points")),
        "reason": str(data.get("reason") or ""),
        "value_for_user": str(data.get("value_for_user") or ""),
        "recommended_action": str(data.get("recommended_action") or ""),
        "main_points": _as_list(data.get("main_points")),
        "activity_time": data.get("activity_time") or None,
        "recommended_push_style": _normalize_choice(
            data.get("recommended_push_style"),
            {"detailed", "brief", "record_only"},
            "brief",
        ),
        "confidence": _normalize_choice(data.get("confidence"), {"high", "medium", "low"}, "medium"),
        "uncertain_fields": _as_list(data.get("uncertain_fields")),
        "raw_json": json.dumps(data, ensure_ascii=False),
    }
    return AIAnalysis(**normalized)


def build_notice_material(notice: Notice) -> dict[str, Any]:
    return {
        "list_title": notice.title,
        "list_publish_time": notice.publish_time,
        "department": notice.department,
        "list_raw_text": notice.raw_text,
        "detail_text": notice.content or "",
        "attachments": [
            {"name": attachment.name, "url": attachment.url}
            for attachment in notice.attachments
        ],
        "source_url": notice.url,
    }


def _build_prompt(notice: Notice, user_profile: dict[str, Any]) -> list[dict[str, str]]:
    user_profile_text = json.dumps(user_profile, ensure_ascii=False, indent=2)
    notice_material = json.dumps(build_notice_material(notice), ensure_ascii=False, indent=2)

    system_prompt = (
        "你是校园通知整理与个性化判断助手。你会收到程序粗略抓取到的网页文本，里面可能有重复标题、"
        "错乱空格、残缺日期或网页噪声。请只根据输入材料整理，不要编造。"
        "判断时必须站在用户画像的角度，而不是站在学校部门或通知发布者的角度。"
        "不要因为通知标题正式、部门重要，就自动判高重要。返回严格 JSON，不要输出 Markdown。"
    )
    user_prompt = f"""
用户画像：
{user_profile_text}

粗糙通知材料：
{notice_material}

判断原则：
1. 优先回答：这条通知是否值得用户现在停下来查看。
2. 如果通知能帮助用户获得竞赛成果、项目经历、实验室机会、技术成长、实习就业机会、证书奖项或重要教务信息，应提高重要等级。
3. 如果通知主要是教师事务、行政流程、公示、采购招标、后勤基建，或没有明确学生参与方式，应降低重要等级。
4. 高重要：与用户专业方向和当前目标强相关，并且有明确报名、申报、参赛、参与项目、加入团队、截止时间、奖项、证书、学分、项目经历、科研经历、实习经历或简历价值。
5. 中重要：与学生有关但不是核心目标，或有一定参考价值但不需要立刻行动。
6. 低重要：与用户成长、专业学习、竞赛、项目、实习就业关系弱，或主要面向教师/行政/采购/后勤/基建。
7. 当前阶段只优化 AI 判断，不改变现有推送流程；recommended_push_style 只给建议，不代表程序会真的过滤消息。

请返回 JSON，字段必须包含：
clean_title: 整理后的干净标题；不确定则为 null
clean_publish_time: 整理后的发布日期，优先 YYYY-MM-DD；不确定则为 null
clean_content: 整理后的通知正文，保留事实，删除重复标题、网页噪声和明显错乱空格，控制在 600 字以内
main_points: 3-5 条主要内容数组，提取原文中的具体事实，不要写空话；短通知可以少于 3 条
importance: high/medium/low，表示对该用户的个人重要程度
personal_relevance: 0-100，表示对该用户画像的个人相关性
category: 通知类型
deadline: 截止日期或关键时间，无法确定则为 null
activity_time: 活动、提交、答辩或会议时间，无法确定则为 null
action_required: 用户需要做什么，无法确定则写“查看原文”
recommended_action: 推荐处理方式，用一句话告诉用户现在该怎么做
target_audience: 适合或涉及的人群数组
key_points: 2-5 条重点数组
reason: 为什么值得或不值得该用户关注，需要结合用户画像说明
value_for_user: 对用户的具体价值，例如竞赛成果、项目经历、实习就业、重要教务、技术成长；没有则写“价值较低”
recommended_push_style: detailed/brief/record_only，表示建议详细提醒、简短提醒或仅记录
confidence: high/medium/low，表示你对判断的置信度
uncertain_fields: 你不确定的字段名数组，例如 ["clean_publish_time", "deadline"]
""".strip()
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def analyze_notice(
    notice: Notice,
    api_key: str | None,
    user_profile: dict[str, Any],
    api_base_url: str = DEFAULT_API_BASE_URL,
    model: str = DEFAULT_MODEL,
    timeout: int = 30,
    post: Callable[..., Any] | None = None,
) -> AIAnalysis | None:
    if not api_key:
        return None

    http_post = post or requests.post
    payload = {
        "model": model,
        "messages": _build_prompt(notice, user_profile),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = http_post(api_base_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return parse_ai_analysis(content)
    except Exception as exc:
        logger.warning("AI analysis failed, skipped AI block: %s", exc)
        return None
