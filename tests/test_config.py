import os
import importlib
import tempfile
import unittest
from pathlib import Path

import config


class ConfigSecurityTests(unittest.TestCase):
    def test_config_file_does_not_contain_secrets(self):
        config_text = Path("config.py").read_text(encoding="utf-8")

        self.assertNotIn("open-apis/bot", config_text)
        self.assertNotIn("sk-", config_text)

    def test_load_env_file_uses_dotenv_without_overriding_existing_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "AI_API_KEY=dotenv-key",
                        "FEISHU_WEBHOOK_URL=\"https://example.com/webhook\"",
                        "AI_ENABLED=false",
                    ]
                ),
                encoding="utf-8",
            )

            original = {
                key: os.environ.get(key)
                for key in ["AI_API_KEY", "FEISHU_WEBHOOK_URL", "AI_ENABLED"]
            }
            try:
                os.environ["AI_API_KEY"] = "environment-key"
                os.environ.pop("FEISHU_WEBHOOK_URL", None)
                os.environ.pop("AI_ENABLED", None)

                config._load_env_file(env_path)

                self.assertEqual(os.environ["AI_API_KEY"], "environment-key")
                self.assertEqual(os.environ["FEISHU_WEBHOOK_URL"], "https://example.com/webhook")
                self.assertEqual(os.environ["AI_ENABLED"], "false")
            finally:
                for key, value in original.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_dry_run_can_be_enabled_from_environment(self):
        original = os.environ.get("DRY_RUN")
        try:
            os.environ["DRY_RUN"] = "true"
            reloaded_config = importlib.reload(config)

            self.assertTrue(reloaded_config.DRY_RUN)
        finally:
            if original is None:
                os.environ.pop("DRY_RUN", None)
            else:
                os.environ["DRY_RUN"] = original
            importlib.reload(config)

    def test_load_user_profile_from_json_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "profile.json"
            profile_path.write_text(
                '{"identity": "测试学生", "stage": "大三", "career_direction": ["后端开发"]}',
                encoding="utf-8",
            )

            profile = config.load_user_profile(profile_path)

        self.assertEqual(profile["identity"], "测试学生")
        self.assertEqual(profile["stage"], "大三")
        self.assertEqual(profile["career_direction"], ["后端开发"])


if __name__ == "__main__":
    unittest.main()
