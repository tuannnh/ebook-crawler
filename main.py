import argparse
import logging
import sys
import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import yaml

from core.dispatcher import get_crawler, close_session, UnsupportedSiteError
from core.merger import filter_by_range, merge
from core.exporter import export
from core.models import Chapter, ChapterContent
from crawlers.base import BaseCrawler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

WORKERS = 5


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_chapters_parallel(crawler: BaseCrawler, toc: list[Chapter], delay: float, workers: int = WORKERS) -> list[ChapterContent]:
    total = len(toc)
    results: dict[int, ChapterContent] = {}
    lock = threading.Lock()
    last_request_time = [0.0]

    def fetch(chapter: Chapter) -> tuple:
        with lock:
            now = time.monotonic()
            wait = delay - (now - last_request_time[0])
            if wait > 0:
                time.sleep(wait)
            last_request_time[0] = time.monotonic()
        try:
            return chapter, crawler.get_chapter_content(chapter)
        except Exception as e:
            logger.warning("  Bo qua chuong '%s': %s", chapter.title, e)
            return chapter, None

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, ch): ch for ch in toc}
        for future in as_completed(futures):
            chapter, content = future.result()
            done += 1
            if content:
                results[chapter.number] = content
                logger.info("  [%d/%d] \u2713 %s", done, total, chapter.title)
            else:
                logger.warning("  [%d/%d] \u2717 %s", done, total, chapter.title)

    return [results[ch.number] for ch in toc if ch.number in results]


def crawl_source(url: str, chapter_range: str | None, config: dict, workers: int = WORKERS) -> tuple:
    crawler = get_crawler(url, config)
    metadata = crawler.get_book_metadata(url)
    max_chapter = int(chapter_range.split("-")[1]) if chapter_range else None
    toc = crawler.get_toc(url, max_chapter=max_chapter)
    toc = filter_by_range(toc, chapter_range)
    logger.info("Tim thay %d chuong tu %s", len(toc), url)
    delay = config["rate_limit"]["delay_seconds"]
    contents = fetch_chapters_parallel(crawler, toc, delay, workers)
    return metadata, contents


def main():
    parser = argparse.ArgumentParser(description="Crawl ebook va xuat ra EPUB/MOBI")
    parser.add_argument("--url", required=True, help="URL trang chu ebook (nguon chinh)")
    parser.add_argument("--chapters", default=None, help="Pham vi chuong nguon chinh, vd: 1-90")
    parser.add_argument("--fill", default=None, help="URL nguon bo sung de lap chuong thieu")
    parser.add_argument("--fill-chapters", default=None, help="Pham vi chuong nguon bo sung, vd: 91-100")
    parser.add_argument("--output", default=None, help="Thu muc luu file dau ra")
    parser.add_argument("--workers", type=int, default=WORKERS, help="So luong worker song song (mac dinh: 5)")
    args = parser.parse_args()

    try:
        config = load_config()
    except FileNotFoundError:
        logger.error("Khong tim thay config.yaml")
        sys.exit(1)

    output_dir = args.output or config.get("output", {}).get("directory", "./output")

    try:
        metadata, contents_a = crawl_source(args.url, args.chapters, config, args.workers)

        contents_b = None
        if args.fill:
            _, contents_b = crawl_source(args.fill, args.fill_chapters, config, args.workers)

        merged = merge(contents_a, contents_b)
        logger.info("Tong so chuong sau khi gop: %d", len(merged))

        epub_path = export(metadata, merged, output_dir)
        print(f"\n[OK] Hoan thanh! File da luu tai: {epub_path}")

    except UnsupportedSiteError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("Loi khong mong doi: %s", e)
        sys.exit(1)
    finally:
        close_session()


if __name__ == "__main__":
    main()
