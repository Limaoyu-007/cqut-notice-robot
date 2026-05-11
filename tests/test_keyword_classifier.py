import unittest

from keyword_classifier import classify_notice_by_keywords
from models import Notice


class KeywordClassifierTests(unittest.TestCase):
    def test_competition_notice_is_high_importance(self):
        notice = Notice(
            title="关于组织大学生程序设计竞赛报名的通知",
            url="https://www.cqut.edu.cn/info/1103/competition.htm",
            content="请学生提交报名表，截止时间为2026年5月20日。",
        )

        result = classify_notice_by_keywords(notice)

        self.assertEqual(result.importance, "high")
        self.assertEqual(result.category, "竞赛实践")
        self.assertIn("竞赛", result.reason)

    def test_procurement_notice_is_low_importance(self):
        notice = Notice(
            title="关于某设备采购招标公告",
            url="https://www.cqut.edu.cn/info/1056/procurement.htm",
            content="采购、招标、资产相关事项。",
        )

        result = classify_notice_by_keywords(notice)

        self.assertEqual(result.importance, "low")
        self.assertEqual(result.category, "行政公告")

    def test_unknown_notice_returns_none(self):
        notice = Notice(
            title="普通通知",
            url="https://www.cqut.edu.cn/info/1101/normal.htm",
            content="内容较少。",
        )

        self.assertIsNone(classify_notice_by_keywords(notice))


if __name__ == "__main__":
    unittest.main()
