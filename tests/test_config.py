import os
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


if __name__ == "__main__":
    unittest.main()
