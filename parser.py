import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import Attachment, Notice


DATE_PATTERNS = [
    r"\d{4}年\d{1,2}月\d{1,2}日",
    r"\d{4}-\d{1,2}-\d{1,2}",
    r"\d{4}/\d{1,2}/\d{1,2}",
    r"\d{4}\.\d{1,2}\.\d{1,2}",
    r"\d{1,2}-\d{1,2}",
]

DEPARTMENT_BY_INFO_ID = {
    "1101": "学校通知",
    "1056": "招标信息",
    "1103": "教务通知",
    "1104": "科研通知",
    "1105": "研究生院通知",
    "1341": "学术讲座",
}


@dataclass
class NoticeDetail:
    title: str | None
    publish_time: str | None
    content: str
    attachments: list[Attachment]


def clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def infer_department(url: str) -> str:
    match = re.search(r"/info/(\d+)/", url)
    if not match:
        return "部门通知"
    return DEPARTMENT_BY_INFO_ID.get(match.group(1), "部门通知")


def normalize_date(text: str | None) -> str | None:
    if not text:
        return None

    text = clean_text(text)
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    match = re.search(r"(\d{1,2})[-/.](\d{1,2})", text)
    if match:
        return match.group(0)

    return None


def extract_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return normalize_date(match.group(0))
    return None


def is_valid_notice_link(title: str, href: str) -> bool:
    if not title or not href:
        return False

    if len(title) < 4:
        return False

    invalid_prefixes = ("#", "javascript:", "mailto:", "tel:")
    if href.startswith(invalid_prefixes):
        return False

    # 过滤明显的导航栏目
    nav_keywords = [
        "首页",
        "学校概况",
        "机构设置",
        "人才培养",
        "科学研究",
        "招生就业",
        "合作交流",
        "通知公告",
        "学校通知",
        "部门通知",
        "教务通知",
        "图书馆通知",
        "招标信息",
    ]

    if title in nav_keywords:
        return False

    # 学校官网详情页一般是 .htm，且通常包含 /info/
    if ".htm" not in href and ".html" not in href:
        return False
        
    if "/info/" not in href:
        return False

    return True


def parse_notices(html: str, list_url: str) -> list[Notice]:
    soup = BeautifulSoup(html, "lxml")

    notices: list[Notice] = []
    seen_urls = set()

    for a in soup.find_all("a"):
        title_node = a.select_one(".title")
        if title_node:
            title = clean_text(title_node.get_text(" ", strip=True))
        else:
            title = clean_text(a.get("title") or a.get_text(" ", strip=True))

        title = re.sub(r"【[^】]+】", "", title)
        title = clean_text(title)
        href = a.get("href")

        if not href:
            continue

        href = href.strip()

        if not is_valid_notice_link(title, href):
            continue

        full_url = urljoin(list_url, href)

        if full_url in seen_urls:
            continue

        seen_urls.add(full_url)

        # 通常日期会在 a 标签的父级或祖先元素文本里
        parent_text = ""
        parent = a.parent
        if parent:
            parent_text = clean_text(parent.get_text(" ", strip=True))

        publish_time = extract_date(parent_text)
        day_node = a.select_one(".day")
        month_node = a.select_one(".month")
        if day_node and month_node:
            publish_time = normalize_date(f"{clean_text(month_node.get_text())}-{clean_text(day_node.get_text())}")

        notice = Notice(
            title=title,
            url=full_url,
            publish_time=publish_time,
            department=infer_department(full_url),
            raw_text=parent_text,
        )

        notices.append(notice)

    return notices


def parse_notice_detail(html: str) -> str:
    return parse_notice_detail_info(html, "").content


def _extract_title_from_page(soup: BeautifulSoup, content_lines: list[str]) -> str | None:
    if soup.title and soup.title.string:
        title = clean_text(soup.title.string)
        title = re.sub(r"[-_—|].*$", "", title).strip()
        if title:
            return title

    h1 = soup.find("h1")
    if h1:
        title = clean_text(h1.get_text(" ", strip=True))
        if title:
            return title

    if content_lines:
        first_line = clean_text(content_lines[0])
        if "通知" in first_line or "公示" in first_line or "公告" in first_line:
            return first_line

    return None


def _extract_attachments(soup: BeautifulSoup, detail_url: str) -> list[Attachment]:
    attachments: list[Attachment] = []
    seen_urls = set()
    for area in soup.select(".Annex, .annexList"):
        for link in area.find_all("a"):
            name = clean_text(link.get_text(" ", strip=True))
            href = link.get("href")
            if not name or not href:
                continue
            full_url = urljoin(detail_url, href.strip())
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            attachments.append(Attachment(name=name, url=full_url))
    return attachments


def parse_notice_detail_info(html: str, detail_url: str) -> NoticeDetail:
    soup = BeautifulSoup(html, "lxml")
    content_div = soup.find(class_="v_news_content") or soup.find(id="vsb_content")
    lines: list[str] = []
    if content_div:
        paragraphs = content_div.find_all("p")
        if paragraphs:
            lines = [clean_text(p.get_text(" ", strip=True)) for p in paragraphs if clean_text(p.get_text(" ", strip=True))]
        else:
            content_text = content_div.get_text("\n", strip=True)
            lines = [clean_text(line) for line in content_text.splitlines() if clean_text(line)]
    elif soup.body:
        content_text = soup.body.get_text("\n", strip=True)
        lines = [clean_text(line) for line in content_text.splitlines() if clean_text(line)]

    title = _extract_title_from_page(soup, lines)
    content_lines = lines[:]
    if title and content_lines and re.sub(r"\s+", "", content_lines[0]) == re.sub(r"\s+", "", title):
        content_lines = content_lines[1:]

    content = "\n".join(content_lines)
    publish_time = None
    for line in reversed(lines):
        publish_time = normalize_date(line)
        if publish_time:
            break

    return NoticeDetail(
        title=title,
        publish_time=publish_time,
        content=content,
        attachments=_extract_attachments(soup, detail_url),
    )
