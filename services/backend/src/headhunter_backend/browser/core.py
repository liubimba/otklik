import asyncio
from pathlib import Path

from patchright.async_api import (
    BrowserContext,
    Cookie,
    Error,
    Page,
    Playwright,
    async_playwright,
)

from headhunter_backend.browser.exceptions import BrowserNetworkError
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.log import get_logger

MAX_ATTEMPTS = 3
RETRY_DELAY = 1


class BrowserCore:
    """Site-agnostic Playwright wrapper: profile-persistent Chromium context,
    page factory, cookie access. All site-specific concerns (login flow,
    auth-cookie inspection) live in the corresponding sites/<site>/auth_flow.py.
    """

    def __init__(self, profile_dir: Path | None = None) -> None:
        self.logger = get_logger(self.__class__.__name__)
        if profile_dir is None:
            self.logger.info("No profile directory provided, using default")
            profile_dir = Path.home() / ".headhunter_ai" / "chrome-profile"
        self.profile_dir = profile_dir
        self.headless = False
        self._context: BrowserContext | None = None
        self._playwright: Playwright | None = None

    async def start(self) -> None:
        self.logger.info(
            "Starting browser with profile directory: ",
            profile_dir=str(self.profile_dir),
        )
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            no_viewport=True,
        )

    async def stop(self) -> None:
        self.logger.info("Stopping browser")
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = None
        self._playwright = None

    async def new_page(self, url: str) -> BrowserPage:
        if self._context is None:
            self.logger.error("BrowserCore is not started")
            raise RuntimeError("BrowserCore is not started")
        for attempt in range(MAX_ATTEMPTS):
            page: Page | None = None
            try:
                self.logger.info("Opening page: ", url=url, attempt=attempt)
                page = await self._context.new_page()
                await page.goto(url)
                return BrowserPage(page)
            except Exception as e:
                if page is not None:
                    await page.close()
                if isinstance(e, Error):
                    self.logger.error(
                        "Failed to open page", url=url, attempt=attempt, error=str(e)
                    )
                else:
                    raise
                if attempt < MAX_ATTEMPTS - 1:
                    self.logger.info(
                        "Sleep before next retry", url=url, delay=RETRY_DELAY
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    raise BrowserNetworkError() from e
        raise RuntimeError("Unreachable")

    async def cookies(self, base_url: str) -> list[Cookie]:
        if self._context is None:
            raise RuntimeError("BrowserCore is not started")
        return await self._context.cookies(base_url)

    async def clear_cookies(self) -> None:
        if self._context is None:
            raise RuntimeError("BrowserCore is not started yet")
        await self._context.clear_cookies()
