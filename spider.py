"""
Scrapy Cloud spider — wraps existing crawl logic as a Scrapy job.

Usage on Scrapy Cloud (via shub):
    shub schedule EbookSpider -s URL=https://truyenfullmoi.com/book.123/ -s CHAPTERS=1-50

Local test:
    scrapy runspider spider.py -s URL=https://truyenfullmoi.com/book.123/ -s CHAPTERS=1-50
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import scrapy
from scrapy.exceptions import CloseSpider

from core.dispatcher import get_crawler, close_session, UnsupportedSiteError
from core.merger import filter_by_range, merge
from core.exporter import export
from core.models import Chapter, ChapterContent
from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "rate_limit": {"delay_seconds": 3},
    "http": {"timeout_seconds": 30, "max_retries": 3, "verify_ssl": False},
    "playwright": {"enabled": False},
    "output": {"directory": "./output"},
}

WORKERS = 5  # parallel chapter fetchers


class EbookSpider(scrapy.Spider):
    name = "ebook"

    def start_requests(self):
        url = getattr(self, "URL", None) or self.settings.get("URL")
        chapters = getattr(self, "CHAPTERS", None) or self.settings.get("CHAPTERS")
        fill_url = getattr(self, "FILL", None) or self.settings.get("FILL")
        fill_chapters = getattr(self, "FILL_CHAPTERS", None) or self.settings.get("FILL_CHAPTERS")
        output_dir = getattr(self, "OUTPUT", None) or self.settings.get("OUTPUT", "./output")

        if not url:
            raise CloseSpider("URL setting is required")

        config = dict(DEFAULT_CONFIG)
        config["output"]["directory"] = output_dir

        try:
            metadata, contents_a = _crawl_source(url, chapters, config)

            contents_b = None
            if fill_url:
                _, contents_b = _crawl_source(fill_url, fill_chapters, config)

            merged = merge(contents_a, contents_b)
            logger.info("Total chapters after merge: %d", len(merged))

            epub_path = export(metadata, merged, output_dir)
            logger.info("[OK] EPUB saved: %s", epub_path)

        except UnsupportedSiteError as e:
            logger.error(str(e))
            raise CloseSpider("unsupported_site")
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            raise CloseSpider("crawl_error")
        finally:
            close_session()

        # Scrapy requires at least one Request — yield a dummy to satisfy the engine
        yield scrapy.Request("about:blank", callback=self.parse, dont_filter=True)

    def parse(self, response):
        pass


def _crawl_source(url: str, chapter_range: str | None, config: dict):
    crawler = get_crawler(url, config)
    metadata = crawler.get_book_metadata(url)
    max_chapter = int(chapter_range.split("-")[1]) if chapter_range else None
    toc = crawler.get_toc(url, max_chapter=max_chapter)
    toc = filter_by_range(toc, chapter_range)
    logger.info("Found %d chapters from %s", len(toc), url)

    contents = _fetch_chapters_parallel(crawler, toc, delay=config["rate_limit"]["delay_seconds"])
    return metadata, contents


def _fetch_chapters_parallel(crawler: BaseCrawler, toc: list[Chapter], delay: float) -> list[ChapterContent]:
    """Fetch chapters in parallel using a thread pool with a shared rate-limit lock."""
    total = len(toc)
    results: dict[int, ChapterContent] = {}
    lock = threading.Lock()
    last_request_time = [0.0]  # mutable container so inner function can write to it

    def fetch(chapter: Chapter) -> tuple[Chapter, ChapterContent | None]:
        # Rate-limit: ensure at least `delay` seconds between any two requests across all threads
        with lock:
            now = time.monotonic()
            wait = delay - (now - last_request_time[0])
            if wait > 0:
                time.sleep(wait)
            last_request_time[0] = time.monotonic()

        try:
            content = crawler.get_chapter_content(chapter)
            return chapter, content
        except Exception as e:
            logger.warning("SKIP '%s': %s", chapter.title, e)
            return chapter, None

    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch, ch): ch for ch in toc}
        for future in as_completed(futures):
            chapter, content = future.result()
            done += 1
            if content:
                results[chapter.number] = content
                logger.info("  [%d/%d] OK %s", done, total, chapter.title)
            else:
                logger.warning("  [%d/%d] SKIP %s", done, total, chapter.title)

    # Return in original TOC order
    return [results[ch.number] for ch in toc if ch.number in results]
