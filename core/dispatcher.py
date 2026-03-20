from urllib.parse import urlparse

from crawlers.base import BaseCrawler
from crawlers.truyenfullmoi import TruyenFullMoiCrawler
from utils.http import HttpClient


class UnsupportedSiteError(Exception):
    pass


_SUPPORTED_SITES = ["truyenfullmoi.com"]


def close_session() -> None:
    pass  # No persistent sessions needed for requests-based crawlers


def get_crawler(url: str, config: dict) -> BaseCrawler:
    domain = urlparse(url).netloc.removeprefix("www.")
    http = HttpClient(config)
    playwright_cfg = config.get("playwright", {})

    if domain == "truyenfullmoi.com":
        return TruyenFullMoiCrawler(http, playwright_cfg, None)

    raise UnsupportedSiteError(
        f"Website '{domain}' not supported.\n"
        f"Supported: {', '.join(_SUPPORTED_SITES)}"
    )
