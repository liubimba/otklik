"""Behavioural tests for HHRUWriter.submit against the current hh.ru flow.

Since 2026-mid hh.ru removed the "submit-on-detail" inline modal that the
writer targeted. Now clicking the vacancy-response-link-top link on the
detail page opens a *dialog* modal — the classic modal selectors
(vacancy-response-submit-popup, add-cover-letter, textarea) live inside
that dialog, not on the detail DOM. The old writer.submit called
`wait_for_selector(respond_button)` right after `new_page(apply_link)`,
which timed out because respond_button appears only *after* clicking
respond_link_top. This suite drives writer.submit through a stubbed
BrowserPage that records the selector sequence and pins the correct
open-modal-then-fill order.
"""

from typing import Any

import pytest

from headhunter_backend.core.site.result import SubmissionResultType
from headhunter_backend.sites.hh_ru.selectors import HHRU_SELECTORS
from headhunter_backend.sites.hh_ru.writer import HHRUWriter


class _StubPage:
    """Minimal BrowserPage double that records the driven UI sequence.

    Every action (wait_for_selector / click / fill / text_content /
    query_selector) is appended to `events` as (action, selector). The
    writer relies on strict call order to prove the modal-open step
    happens before textarea fill.
    """

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
    # min_delay_ms=0 / jitter=0 → no artificial wait inside the human-delay
    # loop; keeps the test fast and deterministic.
    return HHRUWriter(
        core=stub_core,  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )


async def test_writer_opens_modal_before_touching_textarea(
    writer: HHRUWriter, stub_core: _StubCore, stub_page: _StubPage
) -> None:
    """Order-of-operations lock. The new hh.ru flow requires:

      1. open apply_link
      2. wait+click vacancy.respond_link_top on the detail page
      3. wait for response.respond_button — proves the modal is open
      4. click response.open_letter_textarea_button (add-cover-letter)
      5. wait for response.letter_textarea
      6. fill textarea
      7. click response.respond_button (submit)

    Before fix: the writer skips (2)+(3) entirely — it navigates to
    apply_link and immediately awaits respond_button, which never appears
    (it lives inside the modal). Playwright times out, submit returns
    FAILED.
    """
    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/12345", letter_text="dear team"
    )

    assert stub_core.opened_urls == ["https://hh.ru/vacancy/12345"]

    # Ignore query_selector calls (captcha probe) and text_content polls
    # inside _verify — we only care about the UI-driving sequence.
    driving = [
        (action, sel)
        for action, sel in stub_page.events
        if action in ("wait", "click", "fill")
    ]
    respond_link_top = HHRU_SELECTORS.vacancy.respond_link_top
    respond_button = HHRU_SELECTORS.response.respond_button
    open_letter = HHRU_SELECTORS.response.open_letter_textarea_button
    textarea = HHRU_SELECTORS.response.letter_textarea

    # (1)/(2): first the writer waits for the respond link on the detail
    # page and clicks it — no other click may happen before this one.
    assert driving[0] == ("wait", respond_link_top)
    assert driving[1] == ("click", respond_link_top)

    # (3): only after the modal is opened does the writer look for its
    # submit button. This step guards against the pre-fix code path that
    # awaits respond_button as the very first thing.
    assert driving[2] == ("wait", respond_button)

    # (4)+(5)+(6): open letter textarea, wait for it, fill it — in that
    # order. Filling before waiting would race the modal render.
    assert driving[3] == ("click", open_letter)
    assert driving[4] == ("wait", textarea)
    assert driving[5] == ("fill", textarea)

    # (7): final submit click.
    assert driving[6] == ("click", respond_button)

    # Verification loop found "Вы откликнулись" in body → SUBMITTED.
    assert result.type == SubmissionResultType.SUBMITTED
    assert stub_page.closed
