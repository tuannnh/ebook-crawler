# Site Adapter Specifications

Each adapter lives in `crawlers/` and extends `BaseCrawler`. This document describes the known HTML structure of each supported site so adapters can be implemented correctly.

---

## 1. truyenfull.vision

**Domain match:** `truyenfull.vision`

### Book page URL pattern
`https://truyenfull.vision/{slug}/`

### Metadata selectors
| Field | Selector |
|---|---|
| Title | `h3.title` |
| Author | `.info-holder .info a[itemprop="author"]` |
| Description | `div[itemprop="description"]` |
| Cover image | `.book img` → `src` attribute |

### TOC (Table of Contents)
- TOC is paginated — multiple pages of chapter links
- Pagination container: `ul.list-chapter` with `li > a`
- Next page: `ul.pagination li:last-child a` → follow until no next page
- Chapter number: parse from link text e.g. "Chương 1: ..." → extract `1`

### Chapter page
- Content container: `div#chapter-c`
- Clean: remove `div.ads-holder`, `script`, `style` tags inside content

### JS rendering required: NO (static HTML)

---

## 2. truyenfullmoi.com

**Domain match:** `truyenfullmoi.com`

### Book page URL pattern
`https://truyenfullmoi.com/{slug}/`

### Metadata selectors
| Field | Selector |
|---|---|
| Title | `h1.story-title` |
| Author | `.story-info .author a` |
| Description | `.story-intro` |
| Cover image | `.story-cover img` → `src` |

### TOC
- Single page or paginated (TBD — needs live inspection)
- Chapter links: `.chapter-list li a`
- Chapter number: parse from link text

### Chapter page
- Content container: `div.chapter-content`
- Clean: remove ads, scripts

### JS rendering required: UNKNOWN — mark as Playwright fallback candidate

---

## 3. tangthuvien.net

**Domain match:** `tangthuvien.net`

### Book page URL pattern
`https://tangthuvien.net/doc-truyen/{slug}`

### Metadata selectors
| Field | Selector |
|---|---|
| Title | `h1.story-title` or `.book-intro h1` |
| Author | `.book-intro .author` |
| Description | `.book-intro .intro` |
| Cover image | `.book-intro img` → `src` |

### TOC
- Loaded via AJAX — **JS rendering required: YES**
- Playwright must be used to wait for chapter list to render
- Chapter links: `ul.cf li a` after JS load
- Chapter number: parse from link text "Chương X"

### Chapter page
- Content container: `div.box-chap`
- Clean: remove ads, scripts

### JS rendering required: YES (Playwright required)

---

## Adding a New Site Adapter

1. Create `crawlers/{sitename}.py`
2. Extend `BaseCrawler`
3. Implement all 3 required methods
4. Register domain in `core/dispatcher.py` domain map
5. Add selector notes to this spec file

---

- Default author if not found: `"Không rõ tác giả"`
- Default description if not found: `""`
- Default cover if not found: `None`
- All sites use UTF-8
- BeautifulSoup must be initialized with `from_encoding="utf-8"` or let it auto-detect
- Chapter titles and content should be stored as-is (no transliteration)
- EPUB exporter must declare `xml:lang="vi"` in XHTML files
