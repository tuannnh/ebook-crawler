import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from core.models import BookMetadata, Chapter, ChapterContent
from utils.http import HttpClient

logger = logging.getLogger(__name__)

DEFAULT_AUTHOR = "Không rõ tác giả"


class TruyenFullCrawler(BaseCrawler):
    BASE = "https://truyenfull.vision"

    def __init__(self, http: HttpClient):
        self._http = http

    def get_book_metadata(self, url: str) -> BookMetadata:
        soup = BeautifulSoup(self._http.get(url), "lxml")
        title = soup.select_one("h3.title")
        author = soup.select_one('.info-holder .info a[itemprop="author"]')
        description = soup.select_one('div[itemprop="description"]')
        cover = soup.select_one(".book img")
        return BookMetadata(
            title=title.get_text(strip=True) if title else "Không rõ tiêu đề",
            author=author.get_text(strip=True) if author else DEFAULT_AUTHOR,
            description=description.get_text(strip=True) if description else "",
            cover_url=cover["src"] if cover else None,
            source_url=url,
        )

    def get_toc(self, url: str, max_chapter: int | None = None) -> list[Chapter]:
        chapters: list[Chapter] = []
        page_url = url
        seen_urls = set()
        page_num = 0
        while page_url and page_url not in seen_urls:
            seen_urls.add(page_url)
            page_num += 1
            logger.info("Dang tai muc luc trang %d...", page_num)
            soup = BeautifulSoup(self._http.get(page_url), "lxml")
            for a in soup.select("ul.list-chapter li a"):
                title = a.get_text(strip=True)
                href = urljoin(self.BASE, a["href"])
                if not title or not re.search(r"\d", title):
                    continue
                number = _parse_chapter_number(title, len(chapters) + 1)
                chapters.append(Chapter(number=number, title=title, url=href, source="truyenfull.vision"))
            if max_chapter and chapters and chapters[-1].number >= max_chapter:
                break
            next_url = None
            for li in soup.select("ul.pagination li"):
                a = li.select_one("a")
                if not a or not a.get("href"):
                    continue
                sr = li.select_one(".sr-only")
                if sr and "tiếp" in sr.get_text():
                    next_url = urljoin(self.BASE, a["href"].split("#")[0])
                    break
            page_url = next_url if next_url and next_url not in seen_urls else None
        logger.info("Muc luc: %d chuong tren %d trang", len(chapters), page_num)
        return chapters

    def get_chapter_content(self, chapter: Chapter) -> ChapterContent:
        soup = BeautifulSoup(self._http.get(chapter.url), "lxml")
        content_div = soup.select_one("div#chapter-c")
        if content_div:
            for tag in content_div.select("div.ads-holder, script, style"):
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
