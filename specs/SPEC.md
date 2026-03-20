# Ebook Crawler — Master Specification

## Overview
A CLI tool that crawls Vietnamese ebooks from online reading websites and exports them in Kindle-compatible format (EPUB). Supports multi-source crawling to fill missing chapters across different websites.

---

## Output Format
- **Primary:** `.epub` — preserves chapters, TOC, metadata, Vietnamese characters via UTF-8
- **Secondary:** `.mobi` — generated via `kindlegen` or Calibre's `ebook-convert` CLI if available on PATH
- Both files are written to the output directory when possible
- If `kindlegen`/`ebook-convert` is not found, `.mobi` is skipped with a warning and only `.epub` is saved
- File naming: `{ebook_title}.epub` and `{ebook_title}.mobi`

---

## Architecture

```
ebook-crawler/
├── specs/                  # Spec documents (this folder)
├── crawlers/
│   ├── base.py             # Abstract BaseCrawler interface
│   ├── truyenfull.py       # Adapter for truyenfull.vision
│   ├── truyenfullmoi.py    # Adapter for truyenfullmoi.com
│   └── tangthuvien.py      # Adapter for tangthuvien.com
├── core/
│   ├── dispatcher.py       # Detects site from URL, returns correct crawler
│   ├── merger.py           # Merges chapters from multiple sources
│   └── exporter.py         # Builds and writes the .epub file
├── utils/
│   ├── http.py             # Shared HTTP session (requests + rate limiting)
│   ├── ocr.py              # OCR fallback for image-based content
│   └── playwright_helper.py # Playwright fallback for JS-rendered pages
├── main.py                 # CLI entry point
├── config.yaml             # User-configurable settings
└── requirements.txt
```

---

## CLI Interface

```bash
# Single source
python main.py --url "https://truyenfull.vision/ten-truyen/"

# Multi-source merge (fill missing chapters)
python main.py \
  --url "https://truyenfull.vision/ten-truyen/" \
  --fill "https://tangthuvien.net/truyen-toc/ten-truyen/"

# Specify chapter range per source (TOC is always crawled first, then filtered)
python main.py \
  --url "https://truyenfull.vision/ten-truyen/" --chapters 1-90 \
  --fill "https://tangthuvien.net/truyen-toc/ten-truyen/" --fill-chapters 91-100

# Output directory
python main.py --url "..." --output ./books/
```

---

## Core Concepts

### 1. Dispatcher
- Inspects the domain of the input URL
- Returns the matching crawler instance
- Raises `UnsupportedSiteError` if no adapter exists

### 2. BaseCrawler (Abstract Interface)
Every site adapter must implement:
- `get_book_metadata(url) -> BookMetadata` — title, author, description, cover_url
- `get_toc(url) -> list[Chapter]` — ordered list of chapters with title + url
- `get_chapter_content(chapter_url) -> ChapterContent` — title + body text (HTML or plain)

### 3. Merger
- Accepts chapters from multiple sources
- Deduplicates by chapter number
- Fills gaps: if source A is missing chapters 91–100, pulls from source B
- Final output is a sorted, complete chapter list

### 4. Exporter
- Takes merged chapter list + metadata
- Builds a valid EPUB 3 file with:
  - UTF-8 encoding (Vietnamese support)
  - Embedded TOC (NCX + nav.xhtml)
  - One XHTML file per chapter
- After EPUB is written, attempts `.mobi` conversion:
  - Tries `kindlegen {file}.epub` first
  - Falls back to `ebook-convert {file}.epub {file}.mobi` (Calibre)
  - If neither is on PATH, logs a warning and skips `.mobi`

### 5. HTTP Utility
- Shared `requests.Session` with retry logic
- Configurable delay between requests (default: fixed 3s)
- Rotating User-Agent headers
- Playwright fallback triggered when BeautifulSoup returns empty content

### 6. OCR Utility
- Triggered only when a chapter page contains **exclusively** `<img>` tags with no surrounding text (pure image chapter)
- Uses `pytesseract` with Vietnamese language pack (`vie`)
- OCR text appended as full chapter body — images mixed with text paragraphs are ignored (images skipped)
- Out of scope for v1 if rarely encountered; kept as optional utility

---

## Data Models

```python
@dataclass
class BookMetadata:
    title: str
    author: str
    description: str
    cover_url: str | None
    source_url: str

@dataclass
class Chapter:
    number: int        # Used for ordering and dedup across sources
    title: str
    url: str
    source: str        # domain of the source site

@dataclass
class ChapterContent:
    number: int
    title: str
    text: str          # Plain text or cleaned HTML
```

---

## Config (`config.yaml`)

```yaml
rate_limit:
  delay_seconds: 3

http:
  timeout_seconds: 30
  max_retries: 3
  user_agents:
    - "Mozilla/5.0 ..."

ocr:
  enabled: true
  language: "vie"      # Vietnamese tesseract lang pack

playwright:
  enabled: true
  headless: true

output:
  directory: "./output"
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Site not supported | Raise `UnsupportedSiteError`, print helpful message |
| Chapter fetch fails | Log warning, skip chapter, continue |
| All chapters fail | Raise `CrawlError`, abort |
| OCR fails on pure-image chapter | Log warning, insert `[Hình ảnh - OCR thất bại]` placeholder |
| Playwright unavailable | Log warning, fall back to requests only |
| `kindlegen`/`ebook-convert` not found | Log warning, skip `.mobi`, keep `.epub` |
| `.mobi` conversion fails | Log warning, keep `.epub` |

---

## Backlog (Out of Scope for v1)
- Simple UI (web or desktop)
- Login/authentication support
- Image download and embed in EPUB
- Progress resume (checkpoint file)
- Proxy support
