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

from otklik_backend.browser.exceptions import BrowserNetworkError
from otklik_backend.browser.page import BrowserPage
from otklik_backend.browser.window import (
    NoopWindowController,
    WindowController,
    X11WindowController,
)
from otklik_backend.log import get_logger
from otklik_backend.paths import AppPaths

MAX_ATTEMPTS = 3
RETRY_DELAY = 1

APP_WINDOW_NAME = "Otklik"

CHROMIUM_ARGS = [
    "--ozone-platform=x11",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
    "--window-position=-32000,-32000",
]


class BrowserCore:
    def __init__(
        self,
        profile_dir: Path | None = None,
        window: WindowController | None = None,
    ) -> None:
        self.logger = get_logger(self.__class__.__name__)
        if profile_dir is None:
            self.logger.info("No profile directory provided, using default")
            profile_dir = AppPaths().browser_profile
        self.profile_dir = profile_dir
        self.headless = False
        self._context: BrowserContext | None = None
        self._playwright: Playwright | None = None
        if window is not None:
            self._window = window
        elif X11WindowController.available():
            self._window = X11WindowController(self.profile_dir, APP_WINDOW_NAME)
        else:
            self._window = NoopWindowController()

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
            args=CHROMIUM_ARGS,
        )
        await self._window.hide()

    async def show_window(self) -> None:
        await self._window.show_near_app()

    async def hide_window(self) -> None:
        await self._window.hide()

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
                if not isinstance(e, Error):
                    raise
                self.logger.error(
                    "Failed to open page", url=url, attempt=attempt, error=str(e)
                )
                if attempt == MAX_ATTEMPTS - 1:
                    raise BrowserNetworkError() from e
                self.logger.info("Sleep before next retry", url=url, delay=RETRY_DELAY)
                await asyncio.sleep(RETRY_DELAY)
        raise RuntimeError("Unreachable")

    async def cookies(self, base_url: str) -> list[Cookie]:
        if self._context is None:
            raise RuntimeError("BrowserCore is not started")
        return await self._context.cookies(base_url)

    async def clear_cookies(self) -> None:
        if self._context is None:
            raise RuntimeError("BrowserCore is not started yet")
        await self._context.clear_cookies()
