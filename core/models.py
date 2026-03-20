from dataclasses import dataclass, field


@dataclass
class BookMetadata:
    title: str
    author: str
    description: str
    source_url: str
    cover_url: str | None = None


@dataclass
class Chapter:
    number: int
    title: str
    url: str
    source: str


@dataclass
class ChapterContent:
    number: int
    title: str
    text: str
