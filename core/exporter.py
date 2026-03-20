import os
import re
import shutil
import logging
import subprocess
from pathlib import Path

from ebooklib import epub

from core.models import BookMetadata, ChapterContent

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def export(metadata: BookMetadata, chapters: list[ChapterContent], output_dir: str) -> Path:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    epub_path = _write_epub(metadata, chapters, output_dir)
    _try_convert_mobi(epub_path)
    return epub_path


def _write_epub(metadata: BookMetadata, chapters: list[ChapterContent], output_dir: str) -> Path:
    book = epub.EpubBook()
    book.set_language("vi")
    book.set_title(metadata.title)
    book.add_author(metadata.author)
    if metadata.description:
        book.add_metadata("DC", "description", metadata.description)

    epub_chapters: list[epub.EpubHtml] = []
    for ch in chapters:
        body = "\n".join(f"<p>{line}</p>" for line in ch.text.splitlines() if line.strip())
        item = epub.EpubHtml(
            title=ch.title,
            file_name=f"chap_{ch.number:04d}.xhtml",
            lang="vi",
        )
        item.content = (
            f'<?xml version="1.0" encoding="utf-8"?>'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="vi">'
            f"<head><title>{ch.title}</title></head>"
            f"<body><h2>{ch.title}</h2>{body}</body></html>"
        ).encode("utf-8")
        book.add_item(item)
        epub_chapters.append(item)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_chapters

    filename = _safe_filename(metadata.title) + ".epub"
    path = Path(output_dir) / filename
    epub.write_epub(str(path), book)
    logger.info("Đã lưu EPUB: %s", path)
    return path


def _try_convert_mobi(epub_path: Path) -> None:
    mobi_path = epub_path.with_suffix(".mobi")

    if shutil.which("kindlegen"):
        cmd = ["kindlegen", str(epub_path)]
    elif shutil.which("ebook-convert"):
        cmd = ["ebook-convert", str(epub_path), str(mobi_path)]
    else:
        logger.warning("Không tìm thấy kindlegen hoặc ebook-convert. Bỏ qua xuất .mobi.")
        return

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("Đã lưu MOBI: %s", mobi_path)
    except subprocess.CalledProcessError as e:
        logger.warning("Chuyển đổi .mobi thất bại: %s", e.stderr.decode(errors="replace"))
