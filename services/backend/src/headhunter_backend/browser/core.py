import asyncio

from patchright.async_api import async_playwright, Error
from pathlib import Path
from headhunter_backend.log import get_logger
from headhunter_backend.api.schemas import AuthStatusAPISchema
from .page import BrowserPage
from patchright.async_api import BrowserContext, Playwright, Page, Cookie
from headhunter_backend.browser.exceptions import BrowserNetworkError

AUTH_COOKIE_NAME = "hhrole"
AUTHENTICATED_ROLES = frozenset({"applicant", "employer"})

MAX_ATTEMPTS = 3
RETRY_DELAY = 1


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
        self._auth_status = AuthStatusAPISchema.unauthorized()

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
        self._auth_status = AuthStatusAPISchema.unauthorized()

    async def get_auth_status(self) -> AuthStatusAPISchema:
        if self._auth_status.status == "authorizing":
            return self._auth_status
        self._auth_status = AuthStatusAPISchema.from_boolean(
            authenticated=await self._is_authorized()
        )
        return self._auth_status

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        self.logger.info("Waiting for user to log in")
        if self._context is None:
            self.logger.error("BrowserCore is not started")
            raise RuntimeError("BrowserCore is not started")
        self.logger.info("Waiting for user to log in")
        if await self._is_authorized():
            self.logger.info("User is already authenenticated")
            self._auth_status = AuthStatusAPISchema.authorized()
            return
        page: BrowserPage = await self.new_page(f"{self.base_url}/login")
        await page.bring_to_front()
        self._auth_status = AuthStatusAPISchema.authorizing()
        try:
            while not await self._is_authorized():
                self.logger.info("User is not authenticated yet, waiting...")
                await asyncio.sleep(poll_interval)
                if page.is_closed():
                    page = await self.new_page(f"{self.base_url}/login")
        finally:
            if await self._is_authorized():
                self.logger.info("User has logged in")
                self._auth_status = AuthStatusAPISchema.authorized()
            else:
                self._auth_status = AuthStatusAPISchema.unauthorized()
            await page.close()

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
                    raise e
                if attempt < MAX_ATTEMPTS - 1:
                    self.logger.info(
                        "Sleep before next retry", url=url, delay=RETRY_DELAY
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    raise BrowserNetworkError() from e
        raise RuntimeError("Unreachable")

    async def unauthorize(self) -> None:
        if self._context is None:
            raise RuntimeError("BrowserCore is not started yet")
        await self._context.clear_cookies()

    async def _is_authorized(self) -> bool:
        self.logger.info("Checking authentication status")
        if self._context is None:
            self.logger.error("BrowserCore is not started")
            raise RuntimeError("BrowserCore is not started")
        cookies: list[Cookie] = await self._context.cookies(self.base_url)
        for cookie in cookies:
            if cookie["name"] == AUTH_COOKIE_NAME:
                role = cookie["value"]
                if role in AUTHENTICATED_ROLES:
                    self.logger.info("User is authenticated with role: ", role=role)
                    return True
                else:
                    self.logger.warning(
                        "User has unrecognized role in auth cookie: ", role=role
                    )
        return False
