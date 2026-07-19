import asyncio

from patchright.async_api import Cookie

from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger

BASE_URL = "https://hh.ru"
AUTH_COOKIE_NAME = "hhrole"
AUTHENTICATED_ROLES = frozenset({"applicant", "employer"})


class HHRUAuthFlow:
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
        logged_in = False
        try:
            while True:
                if page.is_closed():
                    self._log.info("Login window closed before authentication")
                    break
                if await self._is_authorized():
                    self._log.info("User has logged in")
                    logged_in = True
                    break
                await asyncio.sleep(poll_interval)
        except Exception as error:  # noqa: BLE001
            self._log.warning("Login wait interrupted", error=str(error))
        finally:
            self._auth_status = (
                AuthStatusAPISchema.authorized()
                if logged_in
                else AuthStatusAPISchema.unauthorized()
            )
            await self._safe_close_page(page)
            await self._safe_hide_window()

    async def unauthorize(self) -> None:
        await self._browser.clear_cookies()
        self._auth_status = AuthStatusAPISchema.unauthorized()

    async def _safe_close_page(self, page: BrowserPage) -> None:
        try:
            await page.close()
        except Exception as error:  # noqa: BLE001
            self._log.warning("Failed to close login page", error=str(error))

    async def _safe_hide_window(self) -> None:
        try:
            await self._browser.hide_window()
        except Exception as error:  # noqa: BLE001
            self._log.warning("Failed to hide window", error=str(error))

    async def _is_authorized(self) -> bool:
        self._log.info("Checking authentication status")
        try:
            cookies: list[Cookie] = await self._browser.cookies(BASE_URL)
        except Exception as error:  # noqa: BLE001
            self._log.warning(
                "Failed to read auth cookies (browser closed?)", error=str(error)
            )
            return False
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
