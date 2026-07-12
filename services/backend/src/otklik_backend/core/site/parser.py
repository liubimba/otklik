from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.browser.page import BrowserPage


@runtime_checkable
class SiteParser(Protocol):
    """Per-site parser that streams parsed vacancies from an already-open
    search page. Site-specific selectors are held on the concrete
    implementation (constructor injection) — the protocol stays selector-free.

    NOTE: no `async` keyword on the method — implementations are async
    generators (`async def` + `yield`), which mypy models as functions that
    return an AsyncIterator directly rather than coroutines wrapping one.
    """

    def parse(self, search_page: BrowserPage) -> AsyncIterator[VacancyAPISchema]: ...
