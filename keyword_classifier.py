from models import AIAnalysis, Notice


HIGH_KEYWORDS = ["竞赛", "比赛", "大创", "挑战杯", "互联网+", "实习", "招聘", "宣讲会"]
MEDIUM_KEYWORDS = ["讲座", "培训", "志愿", "活动", "奖学金", "评优"]
LOW_KEYWORDS = ["招标", "采购", "资产", "后勤", "基建", "教师", "公示"]


def _material(notice: Notice) -> str:
    return "\n".join(
        [
            notice.title or "",
            notice.department or "",
            notice.raw_text or "",
            notice.content or "",
        ]
    )


def _contains_any(text: str, keywords: list[str]) -> str | None:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return None


def classify_notice_by_keywords(notice: Notice) -> AIAnalysis | None:
    text = _material(notice)

    high_keyword = _contains_any(text, HIGH_KEYWORDS)
    if high_keyword:
        return AIAnalysis(
            importance="high",
            personal_relevance=75,
            category="竞赛实践" if high_keyword in {"竞赛", "比赛", "大创", "挑战杯", "互联网+"} else "就业实习",
            key_points=[f"命中关键词：{high_keyword}", "建议查看原文确认参与条件和截止时间"],
            reason=f"关键词规则命中“{high_keyword}”，可能和学生参与、竞赛实践或就业机会有关。",
            recommended_action="查看原文确认报名方式、截止时间和附件要求。",
            confidence="medium",
        )

    medium_keyword = _contains_any(text, MEDIUM_KEYWORDS)
    if medium_keyword:
        return AIAnalysis(
            importance="medium",
            personal_relevance=50,
            category="校园活动",
            key_points=[f"命中关键词：{medium_keyword}", "可按兴趣查看原文"],
            reason=f"关键词规则命中“{medium_keyword}”，可能有一定参考价值。",
            recommended_action="有时间可以查看原文。",
            confidence="medium",
        )

    low_keyword = _contains_any(text, LOW_KEYWORDS)
    if low_keyword:
        return AIAnalysis(
            importance="low",
            personal_relevance=10,
            category="行政公告",
            key_points=[f"命中关键词：{low_keyword}", "通常不需要学生立即处理"],
            reason=f"关键词规则命中“{low_keyword}”，通常偏行政、采购或公示信息。",
            recommended_action="无需立即处理。",
            recommended_push_style="record_only",
            confidence="medium",
        )

    return None
