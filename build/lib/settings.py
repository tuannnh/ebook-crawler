BOT_NAME = "ebook-crawler"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# Respect target site rate limits
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1

# Disable Scrapy's built-in HTTP cache (we handle retries in HttpClient)
HTTPCACHE_ENABLED = False

# Scrapy Cloud stores logs — use INFO to avoid noise
LOG_LEVEL = "INFO"

# Required for Scrapy Cloud job output
FEED_EXPORT_ENCODING = "utf-8"
