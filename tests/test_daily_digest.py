import unittest

from daily_digest import format_daily_digest
from models import AIAnalysis, Notice


class DailyDigestTests(unittest.TestCase):
    def test_format_daily_digest_groups_by_importance(self):
        notices = [
            Notice(
                title="高重要竞赛通知",
                url="https://www.cqut.edu.cn/info/1103/high.htm",
                publish_time="2026-05-11",
                ai_analysis=AIAnalysis(
                    importance="high",
                    personal_relevance=90,
                    recommended_action="今天查看并确认报名材料。",
                ),
            ),
            Notice(
                title="中重要讲座通知",
                url="https://www.cqut.edu.cn/info/1341/medium.htm",
                publish_time="2026-05-11",
                ai_analysis=AIAnalysis(
                    importance="medium",
                    personal_relevance=60,
                    recommended_action="有时间可以看看。",
                ),
            ),
            Notice(
                title="低重要采购公告",
                url="https://www.cqut.edu.cn/info/1056/low.htm",
                publish_time="2026-05-11",
                ai_analysis=AIAnalysis(
                    importance="low",
                    personal_relevance=5,
                    recommended_action="无需处理。",
                ),
            ),
        ]

        message = format_daily_digest(notices, date_text="2026-05-11")

        self.assertIn("📬 2026-05-11 通知摘要", message)
        self.assertIn("高重要 1 条", message)
        self.assertIn("1. 高重要竞赛通知", message)
        self.assertIn("今天查看并确认报名材料。", message)
        self.assertIn("中重要 1 条", message)
        self.assertIn("低重要 1 条", message)
        self.assertIn("低重要采购公告", message)

    def test_format_daily_digest_handles_empty_day(self):
        message = format_daily_digest([], date_text="2026-05-11")

        self.assertIn("📬 2026-05-11 通知摘要", message)
        self.assertIn("今天没有记录到新通知。", message)


if __name__ == "__main__":
    unittest.main()
