import logging
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Playwright, Page

logger = logging.getLogger(__name__)

_CF_TITLES = {"just a moment", "attention required"}
_BROWSER_ARGS = ["--disable-blink-features=AutomationControlled"]
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightSession:
    """
    Persistent browser context for the lifetime of a crawl run.
    Always launches headful so Cloudflare challenges can be solved manually.
    On first Cloudflare hit, prints instructions and waits up to 2 minutes
    for the user to complete the challenge before continuing automatically.
    """

    def __init__(self):
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._cf_solved = False  # only prompt once per session

    def _ensure_started(self) -> None:
        if self._context is not None:
            return
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=False,
            args=_BROWSER_ARGS,
        )
        self._context = self._browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )

    def get(self, url: str, wait_selector: str | None = None) -> str:
        self._ensure_started()
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            if not wait_selector:
                return page.content()

            # Check if Cloudflare challenge is blocking
            if self._is_cloudflare(page):
                self._handle_cloudflare(page, url, wait_selector)
            else:
                page.wait_for_selector(wait_selector, timeout=30000)

            return page.content()
        finally:
            page.close()

    def _is_cloudflare(self, page: Page) -> bool:
        return page.title().lower() in _CF_TITLES

    def _handle_cloudflare(self, page: Page, url: str, wait_selector: str) -> None:
        if not self._cf_solved:
            print("\n" + "=" * 60)
            print("[!] Cloudflare challenge detected:")
            print(f"    {url}")
            print()
            print("A browser window is open.")
            print("Please complete the security verification in that window.")
            print("The program will continue automatically once verified.")
            print("=" * 60 + "\n")

        # Wait on the already-open page for the real content to appear
        page.wait_for_selector(wait_selector, timeout=120000)
        self._cf_solved = True
        print("[OK] Verification successful! Continuing crawl...\n")

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._context = self._browser = self._pw = None
