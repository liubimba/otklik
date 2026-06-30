import uuid
from typing import Self

from pydantic import HttpUrl, ValidationError

from headhunter_backend.api.schemas import VacanciesStartSearchRequestAPISchema
from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.log import get_logger
from headhunter_backend.orchestrator.exceptions import (
    FilterSessionClosedError,
    InvalidSearchURLError,
)


class FilterSession:
    def __init__(self, page: BrowserPage) -> None:
        self._id = str(uuid.uuid4())
        self._log = get_logger(self.__class__.__name__)
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
            self._log.info("Closing browser page")
            await self._page.close()

    async def cancel(self) -> None:
        self._log.info("Cancelling filter session")
        if not self._page.is_closed():
            self._log.info("Closing browser page")
            await self._page.close()
        else:
            self._log.warning("Browser page was already closed")

    @classmethod
    async def execute(cls, core: BrowserCore) -> Self:
        page: BrowserPage = await core.new_page("https://hh.ru/search/vacancy")
        return cls(page=page)
