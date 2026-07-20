from urllib.parse import urlparse

from patchright.async_api import Error, Page, Route

from otklik_backend.log import get_logger


class SinglePageGuard:
    def __init__(self, allowed_host: str) -> None:
        self._allowed_host = allowed_host.lower()
        self._locked_page: Page | None = None
        self._log = get_logger(self.__class__.__name__)

    @property
    def active(self) -> bool:
        return self._locked_page is not None

    @property
    def locked_page(self) -> Page | None:
        return self._locked_page

    def lock(self, page: Page) -> None:
        self._locked_page = page
        self._log.info("Locked browser window to a single page")

    def unlock(self) -> None:
        self._locked_page = None
        self._log.info("Unlocked browser window")

    def is_foreign(self, page: Page) -> bool:
        return self._locked_page is not None and page is not self._locked_page

    def host_allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return True
        return host == self._allowed_host or host.endswith(f".{self._allowed_host}")

    async def guard_route(self, route: Route) -> None:
        request = route.request
        try:
            if (
                self._locked_page is not None
                and request.is_navigation_request()
                and request.frame == self._locked_page.main_frame
                and not self.host_allowed(request.url)
            ):
                self._log.info(
                    "Blocked navigation off the allowed host", url=request.url
                )
                await route.abort()
                return
            await route.continue_()
        except Error as exc:
            self._log.warning("Route guard failed", error=str(exc))
