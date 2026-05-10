import unittest

from crawler import create_chromium_options


class CrawlerConfigTests(unittest.TestCase):
    def test_create_chromium_options_uses_configured_browser_path(self):
        options = create_chromium_options(
            user_agent="test-agent",
            browser_path="/usr/bin/chromium-browser",
        )

        self.assertEqual(options.browser_path, "/usr/bin/chromium-browser")

    def test_create_chromium_options_does_not_hardcode_windows_edge(self):
        options = create_chromium_options(user_agent="test-agent", browser_path="")

        self.assertNotEqual(
            options.browser_path,
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        )


if __name__ == "__main__":
    unittest.main()
