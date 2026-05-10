import unittest
import tempfile
from pathlib import Path

from db import DBManager
from models import AIAnalysis, Attachment, Notice
from notifier import format_notice_messages
from parser import infer_department, parse_notice_detail_info


class NoticeDetailParsingTests(unittest.TestCase):
    def test_parse_detail_info_extracts_clean_title_content_date_and_attachments(self):
        html = """
        <html>
          <head><title>关于组织申报测试课程的通知-重庆理工大学</title></head>
          <body>
            <div id="vsb_content">
              <div class="v_news_content">
                <p style="text-align:center"><strong>关于组织申报测试课程的通知</strong></p>
                <p>各教学单位：</p>
                <p>请按要求提交材料，不接受个人申报。</p>
                <p style="text-align:right">教务处</p>
                <p style="text-align:right">2026年4月27日</p>
              </div>
            </div>
            <div class="Annex">
              <strong>附件：</strong>
              <ul>
                <li><a href="/system/download?id=1">1.推荐汇总表.docx</a></li>
                <li><a href="../../files/apply.pdf">2.立项申报书.pdf</a></li>
              </ul>
            </div>
          </body>
        </html>
        """

        detail = parse_notice_detail_info(html, "https://www.cqut.edu.cn/info/1103/70035.htm")

        self.assertEqual(detail.title, "关于组织申报测试课程的通知")
        self.assertEqual(detail.publish_time, "2026-04-27")
        self.assertIn("各教学单位：", detail.content)
        self.assertIn("请按要求提交材料，不接受个人申报。", detail.content)
        self.assertNotIn("附件：", detail.content)
        self.assertEqual(
            detail.attachments,
            [
                Attachment(
                    name="1.推荐汇总表.docx",
                    url="https://www.cqut.edu.cn/system/download?id=1",
                ),
                Attachment(
                    name="2.立项申报书.pdf",
                    url="https://www.cqut.edu.cn/files/apply.pdf",
                ),
            ],
        )

    def test_infer_department_from_detail_url(self):
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1103/70201.htm"), "教务通知")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1104/70198.htm"), "科研通知")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1105/70161.htm"), "研究生院通知")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1101/70201.htm"), "学校通知")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1056/70201.htm"), "招标信息")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/1341/70201.htm"), "学术讲座")
        self.assertEqual(infer_department("https://www.cqut.edu.cn/info/9999/1.htm"), "部门通知")


class FeishuMessageFormattingTests(unittest.TestCase):
    def test_format_notice_messages_pushes_original_content_instead_of_summary(self):
        long_content = "各教学单位：\n" + "这是原文正文。" * 80 + "\n教务处\n2026年4月27日"
        notice = Notice(
            title="关于组织申报测试课程的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="2026-04-27",
            department="教务处",
            content=long_content,
            attachments=[Attachment("1.推荐汇总表.docx", "https://www.cqut.edu.cn/file.docx")],
        )

        messages = format_notice_messages(notice, max_chars=4000)

        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertIn("📢 官方原文", message)
        self.assertIn("关于组织申报测试课程的通知", message)
        self.assertIn("发布时间：2026-04-27", message)
        self.assertIn("正文：\n各教学单位：", message)
        self.assertIn("教务处\n2026年4月27日", message)
        self.assertIn("附件：\n1. 推荐汇总表.docx", message)
        self.assertIn("原文链接：\nhttps://www.cqut.edu.cn/info/1103/70035.htm", message)
        self.assertNotIn("摘要", message)
        self.assertNotIn("...", message)

    def test_format_notice_messages_splits_long_original_content(self):
        notice = Notice(
            title="关于组织申报测试课程的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="2026-04-27",
            department="教务处",
            content="\n".join([f"第{index}段：" + "原文内容" * 20 for index in range(20)]),
        )

        messages = format_notice_messages(notice, max_chars=500)

        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 500 for message in messages))
        self.assertIn("原文链接：", messages[-1])
        self.assertNotIn("原文链接：", messages[0])

    def test_format_notice_messages_uses_compact_ai_notice_card(self):
        notice = Notice(
            title="关于组织申报测试课程的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="2026-04-27",
            department="教务处",
            content="官方正文原文",
            ai_analysis=AIAnalysis(
                importance="high",
                personal_relevance=88,
                clean_title="关于组织申报测试课程的通知",
                clean_publish_time="2026-04-27",
                clean_content="这是 AI 整理后的通知正文，已经去掉重复标题和网页噪声。",
                category="竞赛 / 创新实践",
                deadline="2026-05-12",
                action_required="需要报名",
                target_audience=["计算机类学生"],
                key_points=["是否面向本科生开放", "是否有报名截止时间", "是否能获得项目经历"],
                reason="这条通知和竞赛/项目经历直接相关，可能对简历有价值。",
                recommended_action="建议今天内查看，确认是否需要报名或准备材料。",
                main_points=[
                    "本次申报面向相关课程团队和学生实践项目。",
                    "需要在截止时间前提交申报材料。",
                    "附件中包含报名表和具体要求。",
                ],
                activity_time="2026-05-20",
                confidence="high",
                uncertain_fields=[],
                raw_json='{"importance":"high"}',
            ),
        )

        [message] = format_notice_messages(notice, max_chars=4000)

        self.assertTrue(message.startswith("📢 【高重要】关于组织申报测试课程的通知"))
        self.assertIn("🧠 AI 解读", message)
        self.assertIn("相关度：88/100", message)
        self.assertIn("为什么值得看：这条通知和竞赛/项目经历直接相关，可能对简历有价值。", message)
        self.assertIn("推荐处理：建议今天内查看，确认是否需要报名或准备材料。", message)
        self.assertIn("🎯 重点关注\n1. 是否面向本科生开放\n2. 是否有报名截止时间\n3. 是否能获得项目经历", message)
        self.assertIn("📌 主要内容\n1. 本次申报面向相关课程团队和学生实践项目。", message)
        self.assertIn("2. 需要在截止时间前提交申报材料。", message)
        self.assertIn("3. 附件中包含报名表和具体要求。", message)
        self.assertIn("⏰ 关键时间", message)
        self.assertIn("发布时间：2026-04-27", message)
        self.assertIn("截止时间：2026-05-12", message)
        self.assertIn("活动/提交时间：2026-05-20", message)
        self.assertIn("✅ 行动建议\n建议今天内查看，确认是否需要报名或准备材料。", message)
        self.assertIn("🔗 原文链接\nhttps://www.cqut.edu.cn/info/1103/70035.htm", message)
        self.assertNotIn("这是 AI 整理后的通知正文", message)
        self.assertNotIn("官方正文原文", message)


class NoticeDatabaseTests(unittest.TestCase):
    def test_db_round_trips_attachments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "notices.db"
            db = DBManager(str(db_path))
            notice = Notice(
                title="关于组织申报测试课程的通知",
                url="https://www.cqut.edu.cn/info/1103/70035.htm",
                publish_time="2026-04-27",
                department="教务处",
                raw_text="列表文本",
                content="正文原文",
                attachments=[Attachment("1.推荐汇总表.docx", "https://www.cqut.edu.cn/file.docx")],
                ai_analysis=AIAnalysis(
                    importance="medium",
                    personal_relevance=70,
                    clean_title="关于组织申报测试课程的通知",
                    clean_publish_time="2026-04-27",
                    clean_content="AI 整理后的正文",
                    category="竞赛",
                    deadline=None,
                    action_required="查看原文",
                    target_audience=[],
                    key_points=["关注报名要求"],
                    reason="可能有参考价值。",
                    confidence="medium",
                    uncertain_fields=["deadline"],
                    raw_json='{"importance":"medium"}',
                ),
            )

            db.insert(notice)
            [stored] = db.get_all()
            db.close()

        self.assertEqual(stored.attachments, notice.attachments)
        self.assertEqual(stored.ai_analysis, notice.ai_analysis)


if __name__ == "__main__":
    unittest.main()
