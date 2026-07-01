from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from headhunter_backend.api.schemas import VacancyAPISchema
from headhunter_backend.browser.page import BrowserPage
from headhunter_backend.core.site.selectors import SiteSelectors


@runtime_checkable
class SiteParser(Protocol):
    async def parse(
        self,
        search_page: BrowserPage,
        selectors: SiteSelectors,
    ) -> AsyncIterator[VacancyAPISchema]: ...
