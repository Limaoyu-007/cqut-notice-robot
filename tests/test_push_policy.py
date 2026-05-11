import unittest

from models import AIAnalysis, Notice
from push_policy import DeliveryStyle, decide_delivery_style


class PushPolicyTests(unittest.TestCase):
    def _notice_with_importance(self, importance: str) -> Notice:
        return Notice(
            title="测试通知",
            url=f"https://www.cqut.edu.cn/info/1103/{importance}.htm",
            ai_analysis=AIAnalysis(
                importance=importance,
                personal_relevance=80,
                reason="测试原因",
            ),
        )

    def test_high_importance_uses_detailed_push(self):
        notice = self._notice_with_importance("high")

        self.assertEqual(decide_delivery_style(notice), DeliveryStyle.DETAILED)

    def test_medium_importance_uses_brief_push(self):
        notice = self._notice_with_importance("medium")

        self.assertEqual(decide_delivery_style(notice), DeliveryStyle.BRIEF)

    def test_low_importance_uses_digest_only(self):
        notice = self._notice_with_importance("low")

        self.assertEqual(decide_delivery_style(notice), DeliveryStyle.DIGEST_ONLY)

    def test_notice_without_ai_uses_original_push(self):
        notice = Notice(
            title="无 AI 通知",
            url="https://www.cqut.edu.cn/info/1103/no-ai.htm",
        )

        self.assertEqual(decide_delivery_style(notice), DeliveryStyle.ORIGINAL)

    def test_record_only_recommendation_uses_digest_only(self):
        notice = Notice(
            title="仅记录通知",
            url="https://www.cqut.edu.cn/info/1103/record-only.htm",
            ai_analysis=AIAnalysis(
                importance="medium",
                personal_relevance=20,
                recommended_push_style="record_only",
            ),
        )

        self.assertEqual(decide_delivery_style(notice), DeliveryStyle.DIGEST_ONLY)


if __name__ == "__main__":
    unittest.main()
