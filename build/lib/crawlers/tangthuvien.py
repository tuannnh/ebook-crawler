import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from core.models import BookMetadata, Chapter, ChapterContent
from utils.http import HttpClient
from utils.playwright_helper import PlaywrightSession

logger = logging.getLogger(__name__)

DEFAULT_AUTHOR = "Không rõ tác giả"

# Selector that only appears on the real book/chapter page (not Cloudflare)
_CF_WAIT_SELECTOR_BOOK = "h1.story-title, .book-intro h1, #list-chapter"
_CF_WAIT_SELECTOR_CHAPTER = "div.box-chap"


class TangThuVienCrawler(BaseCrawler):
    BASE = "https://tangthuvien.net"

    def __init__(self, http: HttpClient, session: PlaywrightSession):
        self._http = http
        self._session = session

    def get_book_metadata(self, url: str) -> BookMetadata:
        html = self._session.get(url, wait_selector=_CF_WAIT_SELECTOR_BOOK)
        soup = BeautifulSoup(html, "lxml")
        title = soup.select_one("h1.story-title") or soup.select_one(".book-intro h1")
        author = soup.select_one(".book-intro .author")
        description = soup.select_one(".book-intro .intro")
        cover = soup.select_one(".book-intro img")
        return BookMetadata(
            title=title.get_text(strip=True) if title else "Không rõ tiêu đề",
            author=author.get_text(strip=True) if author else DEFAULT_AUTHOR,
            description=description.get_text(strip=True) if description else "",
            cover_url=cover["src"] if cover else None,
            source_url=url,
        )

    def get_toc(self, url: str) -> list[Chapter]:
        html = self._session.get(url, wait_selector=_CF_WAIT_SELECTOR_BOOK)
        soup = BeautifulSoup(html, "lxml")
        chapters: list[Chapter] = []
        for a in soup.select("ul.cf li a"):
            title = a.get_text(strip=True)
            href = urljoin(self.BASE, a["href"])
            number = _parse_chapter_number(title, len(chapters) + 1)
            chapters.append(Chapter(number=number, title=title, url=href, source="tangthuvien.net"))
        return chapters

    def get_chapter_content(self, chapter: Chapter) -> ChapterContent:
        html = self._session.get(chapter.url, wait_selector=_CF_WAIT_SELECTOR_CHAPTER)
        soup = BeautifulSoup(html, "lxml")
        content_div = soup.select_one("div.box-chap")
        if content_div:
            for tag in content_div.select("script, style"):
                tag.decompose()
            text = content_div.get_text("\n", strip=True)
        else:
            logger.warning("Không tìm thấy nội dung chương: %s", chapter.url)
            text = ""
        return ChapterContent(number=chapter.number, title=chapter.title, text=text)


def _parse_chapter_number(title: str, fallback: int) -> int:
    for pattern in [r"Ch\u01b0\u01a1ng\s*(\d+)", r"Chapter\s*(\d+)", r"^(\d+)"]:
        m = re.search(pattern, title, re.IGNORECASE)
        if m:
            return int(m.group(1))
    logger.warning("Kh\u00f4ng th\u1ec3 x\u00e1c \u0111\u1ecbnh s\u1ed1 ch\u01b0\u01a1ng t\u1eeb ti\u00eau \u0111\u1ec1 '%s', d\u00f9ng th\u1ee9 t\u1ef1: %d", title, fallback)
    return fallback
