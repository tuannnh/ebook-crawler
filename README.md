# ebook-crawler

Crawl chapters from a supported source and export to EPUB (optionally MOBI).

## Supported source

- `truyenfullmoi.com` (wired in `core/dispatcher.py`)

## Requirements

- Python 3.11+ (workspace uses Python 3.12)
- Dependencies from `requirements.txt`
- Optional for MOBI output:
  - `kindlegen` or `ebook-convert` (Calibre)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` as needed:

```yaml
rate_limit:
  delay_seconds: 3

http:
  timeout_seconds: 30
  max_retries: 3
  verify_ssl: false
  user_agents:
    - "..."

output:
  directory: "./output"
```

## Usage

```bash
python main.py --url https://truyenfullmoi.com/book.123/
```

With chapter range, fill source, and workers:

```bash
python main.py \
  --url https://truyenfullmoi.com/book.123/ \
  --chapters 1-50 \
  --fill https://truyenfullmoi.com/book.123/ \
  --fill-chapters 51-60 \
  --output ./output \
  --workers 5
```

## Output

- `./output/<book-title>.epub`
- `./output/<book-title>.mobi` if a converter is available
