from typing import Any

import pytest

from otklik_backend.core.site.result import SubmissionResultType
from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS
from otklik_backend.sites.hh_ru.writer import HHRUWriter


class _StubPage:
    def __init__(self, body_text: str = "Вы откликнулись") -> None:
        self.events: list[tuple[str, str | None]] = []
        self._body_text = body_text
        self.closed = False

    async def wait_for_selector(
        self, selector: str, timeout: float | None = None
    ) -> Any:
        self.events.append(("wait", selector))
        return object()

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))

    async def fill(
        self, selector: str, text: str, timeout: float | None = None
    ) -> None:
        self.events.append(("fill", selector))

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        return None

    async def text_content(self, selector: str) -> str | None:
        self.events.append(("text", selector))
        return self._body_text

    async def close(self) -> None:
        self.closed = True


class _StubCore:
    def __init__(self, page: _StubPage) -> None:
        self._page = page
        self.opened_urls: list[str] = []

    async def new_page(self, url: str) -> _StubPage:
        self.opened_urls.append(url)
        return self._page


@pytest.fixture
def stub_page() -> _StubPage:
    return _StubPage()


@pytest.fixture
def stub_core(stub_page: _StubPage) -> _StubCore:
    return _StubCore(stub_page)


@pytest.fixture
def writer(stub_core: _StubCore) -> HHRUWriter:
    return HHRUWriter(
        core=stub_core,  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )


async def test_writer_opens_modal_before_touching_textarea(
    writer: HHRUWriter, stub_core: _StubCore, stub_page: _StubPage
) -> None:
    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/12345", letter_text="dear team"
    )

    assert stub_core.opened_urls == ["https://hh.ru/vacancy/12345"]

    driving = [
        (action, sel)
        for action, sel in stub_page.events
        if action in ("wait", "click", "fill")
    ]
    respond_link_top = HHRU_SELECTORS.vacancy.respond_link_top
    respond_button = HHRU_SELECTORS.response.respond_button
    open_letter = HHRU_SELECTORS.response.open_letter_textarea_button
    textarea = HHRU_SELECTORS.response.letter_textarea

    assert driving[0] == ("wait", respond_link_top)
    assert driving[1] == ("click", respond_link_top)

    assert driving[2] == ("wait", respond_button)

    assert driving[3] == ("click", open_letter)
    assert driving[4] == ("wait", textarea)
    assert driving[5] == ("fill", textarea)

    assert driving[6] == ("click", respond_button)

    assert result.type == SubmissionResultType.SUBMITTED
    assert stub_page.closed
