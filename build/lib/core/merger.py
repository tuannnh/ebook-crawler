import logging
from core.models import Chapter, ChapterContent

logger = logging.getLogger(__name__)


def filter_by_range(chapters: list[Chapter], chapter_range: str | None) -> list[Chapter]:
    if not chapter_range:
        return chapters
    start, _, end = chapter_range.partition("-")
    lo, hi = int(start), int(end)
    return [c for c in chapters if lo <= c.number <= hi]


def merge(
    contents_a: list[ChapterContent],
    contents_b: list[ChapterContent] | None = None,
) -> list[ChapterContent]:
    merged: dict[int, ChapterContent] = {c.number: c for c in contents_a}

    if contents_b:
        for c in contents_b:
            if c.number not in merged:
                merged[c.number] = c

    if not merged:
        return []

    lo, hi = min(merged), max(merged)
    result: list[ChapterContent] = []
    for n in range(lo, hi + 1):
        if n in merged:
            result.append(merged[n])
        else:
            logger.warning("Chương %d không tìm thấy từ bất kỳ nguồn nào — chèn placeholder.", n)
            result.append(ChapterContent(
                number=n,
                title=f"Chương {n} — Không tìm thấy",
                text="[Chương này không có sẵn từ bất kỳ nguồn nào]",
            ))

    return result
