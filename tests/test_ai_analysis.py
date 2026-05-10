import json
import unittest

from ai_analyzer import _build_prompt, analyze_notice, build_notice_material, parse_ai_analysis
from config import USER_PROFILE
from models import Attachment, Notice


class AIAnalysisParsingTests(unittest.TestCase):
    def test_prompt_uses_personalized_profile_and_rating_rules(self):
        notice = Notice(
            title="关于举办人工智能应用开发比赛的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="2026-05-10",
            department="教务通知",
            content="学生可报名参加，截止时间为2026年5月20日。",
        )

        messages = _build_prompt(notice, USER_PROFILE)
        prompt_text = "\n".join(message["content"] for message in messages)

        self.assertIn("重庆理工大学计算机科学与技术专业本科生", prompt_text)
        self.assertIn("大二下", prompt_text)
        self.assertIn("Java 后端开发", prompt_text)
        self.assertIn("AI 应用工程化", prompt_text)
        self.assertIn("这条通知是否值得用户现在停下来查看", prompt_text)
        self.assertIn("高重要", prompt_text)
        self.assertIn("中重要", prompt_text)
        self.assertIn("低重要", prompt_text)
        self.assertIn("不要因为通知标题正式、部门重要，就自动判高重要", prompt_text)
        self.assertIn("recommended_push_style", prompt_text)

    def test_parse_ai_analysis_normalizes_model_json(self):
        payload = json.dumps(
            {
                "importance": "high",
                "personal_relevance": 82,
                "clean_title": "关于组织程序设计竞赛报名的通知",
                "clean_publish_time": "2026-05-10",
                "clean_content": "学校将组织程序设计竞赛，请计算机类学生关注报名要求。",
                "category": "竞赛 / 创新实践",
                "deadline": "2026-05-12",
                "action_required": "需要报名",
                "target_audience": ["本科生", "计算机类学生"],
                "key_points": ["加入 QQ 群", "提交报名表"],
                "reason": "涉及竞赛经历，对关注比赛的计算机类学生有价值。",
                "value_for_user": "可增加竞赛经历和简历项目素材",
                "recommended_action": "建议今天内查看原文并确认报名材料",
                "main_points": ["学校将组织程序设计竞赛。", "需要在截止日期前提交报名表。"],
                "activity_time": "2026-05-20",
                "recommended_push_style": "detailed",
                "confidence": "high",
                "uncertain_fields": [],
            },
            ensure_ascii=False,
        )

        analysis = parse_ai_analysis(payload)

        self.assertEqual(analysis.importance, "high")
        self.assertEqual(analysis.personal_relevance, 82)
        self.assertEqual(analysis.clean_title, "关于组织程序设计竞赛报名的通知")
        self.assertEqual(analysis.clean_publish_time, "2026-05-10")
        self.assertEqual(analysis.clean_content, "学校将组织程序设计竞赛，请计算机类学生关注报名要求。")
        self.assertEqual(analysis.category, "竞赛 / 创新实践")
        self.assertEqual(analysis.deadline, "2026-05-12")
        self.assertEqual(analysis.action_required, "需要报名")
        self.assertEqual(analysis.target_audience, ["本科生", "计算机类学生"])
        self.assertEqual(analysis.key_points, ["加入 QQ 群", "提交报名表"])
        self.assertEqual(analysis.value_for_user, "可增加竞赛经历和简历项目素材")
        self.assertEqual(analysis.recommended_action, "建议今天内查看原文并确认报名材料")
        self.assertEqual(analysis.main_points, ["学校将组织程序设计竞赛。", "需要在截止日期前提交报名表。"])
        self.assertEqual(analysis.activity_time, "2026-05-20")
        self.assertEqual(analysis.recommended_push_style, "detailed")
        self.assertEqual(analysis.confidence, "high")
        self.assertEqual(analysis.uncertain_fields, [])
        self.assertIn("personal_relevance", analysis.raw_json)

    def test_parse_ai_analysis_clamps_score_and_defaults_missing_fields(self):
        analysis = parse_ai_analysis('{"personal_relevance": 130, "key_points": "查看通知"}')

        self.assertEqual(analysis.importance, "medium")
        self.assertEqual(analysis.personal_relevance, 100)
        self.assertEqual(analysis.category, "未分类")
        self.assertEqual(analysis.deadline, None)
        self.assertEqual(analysis.action_required, "查看原文")
        self.assertEqual(analysis.target_audience, [])
        self.assertEqual(analysis.key_points, ["查看通知"])
        self.assertEqual(analysis.confidence, "medium")
        self.assertEqual(analysis.clean_title, None)
        self.assertEqual(analysis.clean_publish_time, None)
        self.assertEqual(analysis.clean_content, None)
        self.assertEqual(analysis.value_for_user, "")
        self.assertEqual(analysis.recommended_action, "")
        self.assertEqual(analysis.main_points, [])
        self.assertEqual(analysis.activity_time, None)
        self.assertEqual(analysis.recommended_push_style, "brief")
        self.assertEqual(analysis.uncertain_fields, [])

    def test_build_notice_material_keeps_rough_source_for_ai_cleanup(self):
        notice = Notice(
            title="27 2026-04 关于比赛的通知【教务通知】 关于比赛的通知 各学院：...",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="26-04",
            department="教务处",
            raw_text="列表页粗糙文本",
            content="详情页粗糙正文，日期可能混乱。",
            attachments=[Attachment("1.报名表.docx", "https://www.cqut.edu.cn/file.docx")],
        )

        material = build_notice_material(notice)

        self.assertEqual(material["list_title"], notice.title)
        self.assertEqual(material["list_publish_time"], "26-04")
        self.assertEqual(material["detail_text"], "详情页粗糙正文，日期可能混乱。")
        self.assertEqual(material["attachments"][0]["name"], "1.报名表.docx")
        self.assertEqual(material["source_url"], notice.url)


class AIAnalyzerClientTests(unittest.TestCase):
    def test_analyze_notice_returns_none_when_api_key_missing(self):
        notice = Notice(
            title="关于组织竞赛报名的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            content="请在2026年5月12日前报名。",
        )

        analysis = analyze_notice(notice, api_key="", user_profile={"major": "计算机类"})

        self.assertIsNone(analysis)

    def test_analyze_notice_uses_injected_http_client(self):
        calls = []

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "importance": "high",
                                        "personal_relevance": 90,
                                        "clean_title": "关于组织竞赛报名的通知",
                                        "clean_publish_time": "2026-04-27",
                                        "clean_content": "请在2026年5月12日前报名。",
                                        "category": "竞赛",
                                        "key_points": ["按时报名"],
                                        "main_points": ["学生可报名参加竞赛。"],
                                        "reason": "适合关注竞赛的学生。",
                                        "uncertain_fields": [],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

        def fake_post(url, headers, json, timeout):
            calls.append((url, headers, json, timeout))
            return FakeResponse()

        notice = Notice(
            title="关于组织竞赛报名的通知",
            url="https://www.cqut.edu.cn/info/1103/70035.htm",
            publish_time="2026-04-27",
            department="教务处",
            content="请在2026年5月12日前报名。",
        )

        analysis = analyze_notice(
            notice,
            api_key="test-key",
            user_profile={"major": "计算机类", "interests": ["竞赛"]},
            post=fake_post,
        )

        self.assertEqual(analysis.importance, "high")
        self.assertEqual(analysis.personal_relevance, 90)
        self.assertEqual(calls[0][1]["Authorization"], "Bearer test-key")
        self.assertEqual(calls[0][2]["response_format"], {"type": "json_object"})
