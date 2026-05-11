import tempfile
import unittest
from pathlib import Path

import main
from db import DBManager
from models import AIAnalysis, Notice
from push_policy import DeliveryStyle


class MainFlowTests(unittest.TestCase):
    def test_collect_notices_from_sources_merges_multiple_lists_and_deduplicates(self):
        source_html = {
            "https://www.cqut.edu.cn/tzgg/bmtz.htm": """
                <a href="../info/1103/70001.htm">
                  <span class="title">教务通知 A</span>
                  <span class="month">2026-05</span><span class="day">09</span>
                </a>
            """,
            "https://www.cqut.edu.cn/tzgg/xxtz1.htm": """
                <a href="../info/1101/70002.htm">
                  <span class="title">学校通知 B</span>
                  <span class="month">2026-05</span><span class="day">08</span>
                </a>
                <a href="../info/1103/70001.htm">
                  <span class="title">教务通知 A</span>
                  <span class="month">2026-05</span><span class="day">09</span>
                </a>
            """,
        }

        def fetch_stub(url):
            return source_html[url]

        notices = main.collect_notices_from_sources(source_html.keys(), fetch_stub)

        self.assertEqual([notice.title for notice in notices], ["教务通知 A", "学校通知 B"])
        self.assertEqual([notice.department for notice in notices], ["教务通知", "学校通知"])

    def test_process_notice_reuses_cached_ai_analysis(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            db = DBManager(str(Path(temp_dir) / "notices.db"))
            cached_notice = Notice(
                title="缓存通知",
                url="https://www.cqut.edu.cn/info/1103/cache.htm",
                publish_time="2026-05-12",
                department="教务处",
                content="旧正文",
                ai_analysis=AIAnalysis(
                    importance="high",
                    personal_relevance=91,
                    clean_title="缓存标题",
                    clean_publish_time="2026-05-12",
                    clean_content="缓存整理正文",
                    category="竞赛",
                    deadline=None,
                    action_required="查看原文",
                    target_audience=[],
                    key_points=["缓存重点"],
                    reason="缓存原因",
                    confidence="high",
                    raw_json='{"importance":"high"}',
                ),
            )
            db.insert(cached_notice)

            notice = Notice(
                title="缓存通知",
                url=cached_notice.url,
                publish_time="2026-05-12",
                department="教务处",
                content="新抓取正文",
            )
            calls = {"analyze": 0}

            def analyze_stub(notice):
                calls["analyze"] += 1
                return None

            main.attach_ai_analysis(notice, db, analyze_stub, ai_enabled=True)
            db.close()

        self.assertEqual(calls["analyze"], 0)
        self.assertEqual(notice.ai_analysis.clean_content, "缓存整理正文")

    def test_process_notice_dry_run_previews_without_sending(self):
        notice = Notice(
            title="测试通知",
            url="https://www.cqut.edu.cn/info/1103/demo.htm",
            publish_time="2026-05-12",
            department="教务处",
            content="正文",
        )
        sent = []
        previews = []

        def send_stub(notice):
            sent.append(notice)
            return True

        def preview_stub(notice):
            previews.append(notice)

        result = main.deliver_notice(
            notice,
            dry_run=True,
            send_func=send_stub,
            preview_func=preview_stub,
        )

        self.assertTrue(result)
        self.assertEqual(sent, [])
        self.assertEqual(previews, [notice])

    def test_resolve_dry_run_uses_cli_or_environment_switch(self):
        self.assertTrue(main.resolve_dry_run(cli_dry_run=True, env_dry_run=False))
        self.assertTrue(main.resolve_dry_run(cli_dry_run=False, env_dry_run=True))
        self.assertFalse(main.resolve_dry_run(cli_dry_run=False, env_dry_run=False))

    def test_deliver_notice_skips_digest_only_notice(self):
        notice = Notice(
            title="低重要通知",
            url="https://www.cqut.edu.cn/info/1103/low.htm",
            ai_analysis=AIAnalysis(importance="low", personal_relevance=10),
        )
        sent = []
        previews = []

        result = main.deliver_notice(
            notice,
            dry_run=False,
            delivery_style=DeliveryStyle.DIGEST_ONLY,
            send_func=lambda notice, style=None: sent.append((notice, style)) or True,
            preview_func=lambda notice: previews.append(notice),
        )

        self.assertTrue(result)
        self.assertEqual(sent, [])
        self.assertEqual(previews, [])

    def test_deliver_notice_passes_brief_style_to_sender(self):
        notice = Notice(
            title="中重要通知",
            url="https://www.cqut.edu.cn/info/1103/medium.htm",
            ai_analysis=AIAnalysis(importance="medium", personal_relevance=55),
        )
        sent = []

        result = main.deliver_notice(
            notice,
            dry_run=False,
            delivery_style=DeliveryStyle.BRIEF,
            send_func=lambda notice, style=None: sent.append((notice, style)) or True,
        )

        self.assertTrue(result)
        self.assertEqual(sent, [(notice, "brief")])

    def test_send_daily_digest_formats_and_sends_today_notices(self):
        notices = [
            Notice(
                title="今日通知",
                url="https://www.cqut.edu.cn/info/1103/today.htm",
                publish_time="2026-05-11",
                ai_analysis=AIAnalysis(
                    importance="low",
                    personal_relevance=8,
                    recommended_action="无需立即处理。",
                ),
            )
        ]
        sent = []

        class FakeDB:
            def get_by_publish_date(self, date_text):
                self.date_text = date_text
                return notices

            def close(self):
                return None

        result = main.send_daily_digest(
            date_text="2026-05-11",
            db_factory=lambda path: FakeDB(),
            send_text_func=lambda message: sent.append(message) or True,
        )

        self.assertTrue(result)
        self.assertEqual(len(sent), 1)
        self.assertIn("2026-05-11 通知摘要", sent[0])
        self.assertIn("今日通知", sent[0])
