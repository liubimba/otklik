from patchright.async_api import async_playwright
from pathlib import Path
from headhunter_backend.log import get_logger
from .page import BrowserPage
from patchright.async_api import BrowserContext, Playwright, Page


class BrowserCore:
    def __init__(
        self, profile_dir: Path | None = None, base_url: str = "https://hh.ru"
    ):
        self.logger = get_logger(self.__class__.__name__)
        if profile_dir is None:
            self.logger.info("No profile directory provided, using default")
            profile_dir = Path.home() / ".headhunter_ai" / "chrome-profile"
        self.profile_dir = profile_dir
        self.headless = False
        self.base_url = base_url
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
            user_data_dir=str(self.profile_dir), headless=self.headless
        )

    async def stop(self) -> None:
        self.logger.info("Stopping browser")
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = None
        self._playwright = None

    async def is_authenticated(self) -> bool:
        self.logger.info("Checking authentication status")
        if self._context is None:
            self.logger.error("BrowserCore is not started")
            raise RuntimeError("BrowserCore is not started")
        page: BrowserPage = await self.new_page("{}/{}".format(self.base_url, "login"))
        is_authenticated = page.get_url().find("/login") == -1
        await page.close()
        self.logger.info("Authentication status: ", is_authenticated=is_authenticated)
        return is_authenticated

    async def new_page(self, url: str) -> BrowserPage:
        self.logger.info("Opening page: ", url=url)
        if self._context is None:
            self.logger.error("BrowserCore is not started")
            raise RuntimeError("BrowserCore is not started")
        page: Page = await self._context.new_page()
        await page.goto(url)
        return BrowserPage(page)
