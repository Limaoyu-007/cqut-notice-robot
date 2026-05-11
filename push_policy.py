from enum import StrEnum

from models import Notice


class DeliveryStyle(StrEnum):
    DETAILED = "detailed"
    BRIEF = "brief"
    DIGEST_ONLY = "digest_only"
    ORIGINAL = "original"


def decide_delivery_style(notice: Notice) -> DeliveryStyle:
    analysis = notice.ai_analysis
    if analysis is None:
        return DeliveryStyle.ORIGINAL

    if analysis.recommended_push_style == "record_only":
        return DeliveryStyle.DIGEST_ONLY
    if analysis.recommended_push_style == "detailed":
        return DeliveryStyle.DETAILED

    if analysis.importance == "high":
        return DeliveryStyle.DETAILED
    if analysis.importance == "low":
        return DeliveryStyle.DIGEST_ONLY

    return DeliveryStyle.BRIEF
