import asyncio
from urllib.parse import urlparse

from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger

BASE_URL = "https://career.habr.com"
LOGIN_URL = "https://career.habr.com/users/auth/tmid"
AUTH_HOST = "career.habr.com"
SIGN_IN_MARKER = ".user-auth-menu__sign_in"


class HabrAuthFlow:
    def __init__(self, browser: BrowserCore) -> None:
        self._browser = browser
        self._log = get_logger(self.__class__.__name__)
        self._auth_status = AuthStatusAPISchema.unauthorized()

    async def get_auth_status(self) -> AuthStatusAPISchema:
        if self._auth_status.status == "authorizing":
            return self._auth_status
        authenticated = await self._is_authorized()
        self._auth_status = AuthStatusAPISchema.from_boolean(
            authenticated=authenticated
        )
        return self._auth_status

    async def wait_for_login(self, poll_interval: float = 1.5) -> None:
        self._log.info("Waiting for user to log in to Habr")
        page: BrowserPage = await self._browser.new_page(LOGIN_URL)
        await self._browser.show_window()
        await page.bring_to_front()
        self._auth_status = AuthStatusAPISchema.authorizing()
        logged_in = False
        try:
            while True:
                if page.is_closed():
                    self._log.info("Login window closed before authentication")
                    break
                if await self._page_shows_authenticated(page):
                    self._log.info("User has logged in to Habr")
                    logged_in = True
                    break
                await asyncio.sleep(poll_interval)
        except Exception as error:  # noqa: BLE001
            self._log.warning("Habr login wait interrupted", error=str(error))
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

    async def _is_authorized(self) -> bool:
        try:
            page = await self._browser.new_page(BASE_URL)
        except Exception as error:  # noqa: BLE001
            self._log.warning("Habr auth probe failed", error=str(error))
            return False
        try:
            authenticated = await self._page_shows_authenticated(page)
        finally:
            await self._safe_close_page(page)
            await self._safe_hide_window()
        return authenticated

    async def _page_shows_authenticated(self, page: BrowserPage) -> bool:
        host = (urlparse(page.get_url()).hostname or "").lower()
        if host != AUTH_HOST and not host.endswith(f".{AUTH_HOST}"):
            return False
        return await page.query_selector(SIGN_IN_MARKER) is None

    async def _safe_close_page(self, page: BrowserPage) -> None:
        try:
            await page.close()
        except Exception as error:  # noqa: BLE001
            self._log.warning("Failed to close Habr auth page", error=str(error))

    async def _safe_hide_window(self) -> None:
        try:
            await self._browser.hide_window()
        except Exception as error:  # noqa: BLE001
            self._log.warning("Failed to hide window", error=str(error))
