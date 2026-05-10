from DrissionPage import ChromiumOptions, ChromiumPage


def create_chromium_options(user_agent: str, browser_path: str = "") -> ChromiumOptions:
    options = ChromiumOptions()
    options.headless(True)
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    if browser_path:
        options.set_browser_path(browser_path)
    options.set_user_agent(user_agent)
    return options


class NoticeCrawler:
    def __init__(self, user_agent: str, browser_path: str = ""):
        print("初始化 DrissionPage 浏览器...")
        self.page = ChromiumPage(create_chromium_options(user_agent, browser_path))

    def fetch_html(self, url: str, timeout: int = 15) -> str:
        print(f"准备抓取：{url}")
        try:
            self.page.get(url, timeout=timeout)
            self.page.wait(2)

            html = self.page.html
            status = self.page.response.status if hasattr(self.page, "response") and self.page.response else "未知"
            print(f"状态码：{status}")
            print(f"响应长度：{len(html)}")
            return html
        except Exception as e:
            print(f"抓取失败：{e}")
            return ""

    def close(self):
        self.page.quit()
