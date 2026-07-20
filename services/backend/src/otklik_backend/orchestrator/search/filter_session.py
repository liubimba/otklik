import uuid
from typing import Self
from urllib.parse import urlparse

from pydantic import HttpUrl, ValidationError

from otklik_backend.api.schemas import VacanciesStartSearchRequestAPISchema
from otklik_backend.browser.core import BrowserCore
from otklik_backend.browser.page import BrowserPage
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.exceptions import (
    FilterSessionClosedError,
    InvalidSearchURLError,
)

SEARCH_URL = "https://hh.ru/search/vacancy"


class FilterSession:
    def __init__(self, core: BrowserCore, page: BrowserPage) -> None:
        self._id = str(uuid.uuid4())
        self._log = get_logger(self.__class__.__name__)
        self._core = core
        self._page = page
        self._confirmed = False

        self._log.info("Issued new filter session", id=self._id)

    @property
    def id(self) -> str:
        return self._id

    async def confirm(self) -> str:
        self._log.info("Confirming filter session")
        if self._confirmed:
            self._log.error("Filter session already confirmed")
            raise FilterSessionClosedError()

        self._confirmed = True

        if self._page.is_closed():
            self._log.error("Cannot confirm: browser page is already closed")
            raise FilterSessionClosedError()

        url = self._page.get_url()
        try:
            VacanciesStartSearchRequestAPISchema(url=HttpUrl(url=url))
            return url
        except ValidationError as exc:
            self._log.error("Invalid browser page URL", error=str(exc))
            raise InvalidSearchURLError() from exc
        finally:
            await self._core.unlock_window()
            self._log.info("Closing browser page")
            await self._page.close()

    async def cancel(self) -> None:
        self._log.info("Cancelling filter session")
        await self._core.unlock_window()
        if not self._page.is_closed():
            self._log.info("Closing browser page")
            await self._page.close()
        else:
            self._log.warning("Browser page was already closed")

    @classmethod
    async def execute(cls, core: BrowserCore) -> Self:
        page: BrowserPage = await core.new_page(SEARCH_URL)
        host = urlparse(SEARCH_URL).hostname or ""
        await core.lock_window(page, host)
        return cls(core=core, page=page)
