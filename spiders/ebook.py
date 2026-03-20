"""
Scrapy Cloud spider — wraps existing crawl logic as a Scrapy job.

Usage on Scrapy Cloud (via shub):
    shub schedule ebook -s URL=https://truyenfullmoi.com/book.123/ -s CHAPTERS=1-50
    shub schedule ebook -s URL=... -s CHAPTERS=1-50 -s COPYPARTY_PW=<password> -s COPYPARTY_DIR=/ebooks/

Local test:
    scrapy crawl ebook -s URL=https://truyenfullmoi.com/book.123/ -s CHAPTERS=1-50
"""

import logging
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import scrapy
from scrapy.exceptions import CloseSpider

from core.dispatcher import get_crawler, close_session, UnsupportedSiteError
from core.merger import filter_by_range, merge
from core.exporter import export
from core.models import Chapter, ChapterContent
from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

COPYPARTY_URL = "https://copy.hungtuan.me"

DEFAULT_CONFIG = {
    "rate_limit": {"delay_seconds": 3},
    "http": {
        "timeout_seconds": 30,
        "max_retries": 3,
        "verify_ssl": False,
        "user_agents": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ],
    },
    "playwright": {"enabled": False},
    "output": {"directory": "./output"},
}

WORKERS = 5


class EbookSpider(scrapy.Spider):
    name = "ebook"

    def start_requests(self):
        url = getattr(self, "URL", "") or self.settings.get("URL", "")
        chapters = getattr(self, "CHAPTERS", "") or None
        fill_url = getattr(self, "FILL", "") or None
        fill_chapters = getattr(self, "FILL_CHAPTERS", "") or None
        output_dir = getattr(self, "OUTPUT", "./output") or "./output"
        copyparty_pw = getattr(self, "COPYPARTY_PW", "") or None
        workers = int(getattr(self, "WORKERS", WORKERS))

        if not url:
            raise CloseSpider("URL setting is required")

        config = dict(DEFAULT_CONFIG)
        config["output"]["directory"] = output_dir

        try:
            metadata, contents_a = _crawl_source(url, chapters, config, workers)

            contents_b = None
            if fill_url:
                _, contents_b = _crawl_source(fill_url, fill_chapters, config, workers)

            merged = merge(contents_a, contents_b)
            logger.info("Total chapters after merge: %d", len(merged))

            epub_path = export(metadata, merged, output_dir)
            logger.info("[OK] EPUB saved: %s", epub_path)

            if copyparty_pw:
                _copyparty_upload(epub_path, copyparty_pw)
            else:
                logger.warning("COPYPARTY_PW not set — skipping upload")

        except UnsupportedSiteError as e:
            logger.error(str(e))
            raise CloseSpider("unsupported_site")
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            raise CloseSpider("crawl_error")
        finally:
            close_session()

        yield scrapy.Request("about:blank", callback=self.parse, dont_filter=True)

    def parse(self, response):
        pass


def _copyparty_upload(epub_path: Path, password: str) -> None:
    """Upload epub (and mobi if exists) to copyparty under /ebooks/<book_title>/"""
    book_folder = epub_path.stem  # same as _safe_filename(title)
    files_to_upload = [epub_path]
    mobi_path = epub_path.with_suffix(".mobi")
    if mobi_path.exists():
        files_to_upload.append(mobi_path)

    for path in files_to_upload:
        upload_url = f"{COPYPARTY_URL}/ebooks/{book_folder}/{path.name}"
        with open(path, "rb") as f:
            resp = requests.put(
                upload_url,
                data=f,
                headers={"pw": password},
                verify=False,
                timeout=120,
            )
        resp.raise_for_status()
        logger.info("[OK] Uploaded: %s", upload_url)


def _crawl_source(url: str, chapter_range: str | None, config: dict, workers: int = WORKERS):
    crawler = get_crawler(url, config)
    metadata = crawler.get_book_metadata(url)
    max_chapter = int(chapter_range.split("-")[1]) if chapter_range else None
    toc = crawler.get_toc(url, max_chapter=max_chapter)
    toc = filter_by_range(toc, chapter_range)
    logger.info("Found %d chapters from %s", len(toc), url)
    contents = _fetch_chapters_parallel(crawler, toc, delay=config["rate_limit"]["delay_seconds"], workers=workers)
    return metadata, contents


def _fetch_chapters_parallel(crawler: BaseCrawler, toc: list[Chapter], delay: float, workers: int = WORKERS) -> list[ChapterContent]:
    total = len(toc)
    results: dict[int, ChapterContent] = {}
    lock = threading.Lock()
    last_request_time = [0.0]

    def fetch(chapter: Chapter) -> tuple[Chapter, ChapterContent | None]:
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
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, ch): ch for ch in toc}
        for future in as_completed(futures):
            chapter, content = future.result()
            done += 1
            if content:
                results[chapter.number] = content
                logger.info("  [%d/%d] OK %s", done, total, chapter.title)
            else:
                logger.warning("  [%d/%d] SKIP %s", done, total, chapter.title)

    return [results[ch.number] for ch in toc if ch.number in results]
