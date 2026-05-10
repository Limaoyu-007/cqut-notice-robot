import tempfile
import unittest
from pathlib import Path

import main
from db import DBManager
from models import AIAnalysis, Notice


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
