from abc import ABC, abstractmethod
from core.models import BookMetadata, Chapter, ChapterContent


class BaseCrawler(ABC):
    @abstractmethod
    def get_book_metadata(self, url: str) -> BookMetadata:
        """Fetch title, author, description, cover from the book's main page."""

    @abstractmethod
    def get_toc(self, url: str, max_chapter: int | None = None) -> list[Chapter]:
        """Return ordered list of chapters. Stops early if max_chapter is reached."""

    @abstractmethod
    def get_chapter_content(self, chapter: Chapter) -> ChapterContent:
        """Fetch and return the text content of a single chapter."""
