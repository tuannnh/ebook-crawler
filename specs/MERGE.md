# Multi-Source Merge Specification

## Problem
A single website may not have all chapters of an ebook. The tool must allow the user to specify a second (or more) source URL to fill in missing chapters.

---

## Merge Strategy

### Input
- Source A: chapters crawled from `--url` (with optional `--chapters` range)
- Source B: chapters crawled from `--fill` (with optional `--fill-chapters` range)

### Deduplication Rule
- Chapter identity = **chapter number** (integer)
- If the same chapter number exists in both sources, **Source A takes priority**
- Source B only fills chapters whose numbers are absent in Source A

### Gap Detection
- After crawling Source A, the merger computes the expected range: `min(chapter_numbers)` to `max(chapter_numbers)`
- Any integer in that range not present = a gap
- Gaps are reported to the user before fetching Source B

### Output
- A single sorted list of `ChapterContent` objects ordered by `chapter.number`
- Gaps that could not be filled from any source are logged as warnings
- A placeholder chapter is inserted for unfillable gaps:
  ```
  Title: "Chương {N} — Không tìm thấy"
  Text:  "[Chương này không có sẵn từ bất kỳ nguồn nào]"
  ```

---

## Chapter Number Parsing

Chapter numbers must be reliably extracted from chapter titles. Rules (in priority order):

1. Regex match on `Chương\s+(\d+)` (Vietnamese standard)
2. Regex match on `Chapter\s+(\d+)` (English fallback)
3. Regex match on leading integer in title string
4. If none match: assign sequential index based on TOC order (log a warning)

---

## CLI Examples

```bash
# Auto-detect gaps and fill from second source
python main.py \
  --url "https://truyenfull.vision/truyen-a/" \
  --fill "https://tangthuvien.net/truyen-toc/truyen-a/"

# Explicit ranges (TOC always crawled first, then filtered to range)
python main.py \
  --url "https://truyenfull.vision/truyen-a/" --chapters 1-90 \
  --fill "https://tangthuvien.net/truyen-toc/truyen-a/" --fill-chapters 91-100
```

---

## Merge Flow Diagram

```
[Crawl Source A] --> [Chapter list A]
                                      \
                                       --> [Merger] --> [Sorted complete list] --> [Exporter]
                                      /
[Crawl Source B] --> [Chapter list B]
```

---

## Edge Cases

| Case | Behavior |
|---|---|
| Source B has chapters already in A | Ignored (A takes priority) |
| Source B also missing the gap chapters | Log warning, insert placeholder |
| Chapter ranges overlap | A wins on overlap, B fills only true gaps |
| No `--fill` provided but gaps exist | Log warning, insert placeholders, continue export |
| Chapter numbers non-sequential (e.g. 1,2,5,6) | Only gaps within declared range are flagged |
