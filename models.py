from dataclasses import dataclass, field


@dataclass
class Attachment:
    name: str
    url: str


@dataclass
class AIAnalysis:
    importance: str = "medium"
    personal_relevance: int = 0
    clean_title: str | None = None
    clean_publish_time: str | None = None
    clean_content: str | None = None
    category: str = "未分类"
    deadline: str | None = None
    action_required: str = "查看原文"
    target_audience: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    reason: str = ""
    value_for_user: str = ""
    recommended_action: str = ""
    main_points: list[str] = field(default_factory=list)
    activity_time: str | None = None
    recommended_push_style: str = "brief"
    confidence: str = "medium"
    uncertain_fields: list[str] = field(default_factory=list)
    raw_json: str | None = None


@dataclass
class Notice:
    title: str
    url: str
    publish_time: str | None = None
    department: str | None = None
    raw_text: str | None = None
    content: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    ai_analysis: AIAnalysis | None = None
