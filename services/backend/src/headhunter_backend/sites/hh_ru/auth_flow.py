import asyncio

from patchright.async_api import Cookie

from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.log import get_logger

BASE_URL = "https://hh.ru"
AUTH_COOKIE_NAME = "hhrole"
AUTHENTICATED_ROLES = frozenset({"applicant", "employer"})


class HHRUAuthFlow:
    """HH.ru-specific login handling. Wraps a generic BrowserCore and inspects
    the `hhrole` cookie to decide whether the user is authenticated."""

    def __init__(self, browser: BrowserCore) -> None:
        self._browser = browser
        self._log = get_logger(self.__class__.__name__)
        self._auth_status = AuthStatusAPISchema.unauthorized()

    async def get_auth_status(self) -> AuthStatusAPISchema:
        if self._auth_status.status == "authorizing":
            return self._auth_status
        self._auth_status = AuthStatusAPISchema.from_boolean(
            authenticated=await self._is_authorized()
        )
        return self._auth_status

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        self._log.info("Waiting for user to log in")
        if await self._is_authorized():
            self._log.info("User is already authenticated")
            self._auth_status = AuthStatusAPISchema.authorized()
            return
        page: BrowserPage = await self._browser.new_page(f"{BASE_URL}/login")
        await self._browser.show_window()
        await page.bring_to_front()
        self._auth_status = AuthStatusAPISchema.authorizing()
        try:
            while not await self._is_authorized():
                self._log.info("User is not authenticated yet, waiting...")
                await asyncio.sleep(poll_interval)
                if page.is_closed():
                    page = await self._browser.new_page(f"{BASE_URL}/login")
        finally:
            if await self._is_authorized():
                self._log.info("User has logged in")
                self._auth_status = AuthStatusAPISchema.authorized()
            else:
                self._auth_status = AuthStatusAPISchema.unauthorized()
            await page.close()
            await self._browser.hide_window()

    async def unauthorize(self) -> None:
        await self._browser.clear_cookies()
        self._auth_status = AuthStatusAPISchema.unauthorized()

    async def _is_authorized(self) -> bool:
        self._log.info("Checking authentication status")
        cookies: list[Cookie] = await self._browser.cookies(BASE_URL)
        for cookie in cookies:
            if cookie["name"] == AUTH_COOKIE_NAME:
                role = cookie["value"]
                if role in AUTHENTICATED_ROLES:
                    self._log.info("User is authenticated with role: ", role=role)
                    return True
                self._log.warning(
                    "User has unrecognized role in auth cookie: ", role=role
                )
        return False
