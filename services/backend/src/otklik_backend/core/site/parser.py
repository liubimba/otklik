from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.browser.page import BrowserPage


@runtime_checkable
class SiteParser(Protocol):
    def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]: ...
