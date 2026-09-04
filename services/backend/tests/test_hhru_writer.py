from typing import Any

import pytest

from otklik_backend.core.site.result import SubmissionResultType
from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS
from otklik_backend.sites.hh_ru.writer import HHRUWriter


class _StubPage:
    def __init__(self, body_text: str = "Вы откликнулись") -> None:
        self.events: list[tuple[str, str | None]] = []
        self._body_text = body_text
        self.values: dict[str, str] = {}
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
        self.values[selector] = text

    async def input_value(self, selector: str, timeout: float | None = None) -> str:
        self.events.append(("input_value", selector))
        return self.values.get(selector, "")

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        if selector in (
            HHRU_SELECTORS.response.open_letter_textarea_button,
            HHRU_SELECTORS.response.respond_button,
        ):
            return object()
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

    async def open_reusable_page(self, key: str, url: str) -> _StubPage:
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


class _FormStubPage(_StubPage):
    def __init__(self, present: set[str]) -> None:
        super().__init__(body_text="")
        self._present = present
        self._submitted = False

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        return object() if selector in self._present else None

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))
        response = HHRU_SELECTORS.response
        if selector in (response.respond_button, response.respond_no_test_button):
            self._submitted = True

    async def text_content(self, selector: str) -> str | None:
        self.events.append(("text", selector))
        return "Вы откликнулись" if self._submitted else ""


async def test_writer_skips_the_vacancy_when_an_employer_test_is_present_even_with_the_no_questions_link() -> (
    None
):
    response = HHRU_SELECTORS.response
    page = _FormStubPage(
        present={
            response.respond_button,
            response.employer_test_marker,
            response.respond_no_test_button,
        }
    )
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/135583370", letter_text="dear team"
    )

    assert result.type == SubmissionResultType.FAILED
    assert result.reason is not None and "тест" in result.reason.lower()
    assert ("click", response.respond_no_test_button) not in page.events
    assert ("click", response.respond_button) not in page.events


class _EmptyLetterStubPage(_FormStubPage):
    async def input_value(self, selector: str, timeout: float | None = None) -> str:
        self.events.append(("input_value", selector))
        return ""


async def test_writer_does_not_respond_when_the_letter_field_stays_empty() -> None:
    response = HHRU_SELECTORS.response
    page = _EmptyLetterStubPage(present={response.respond_button})
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/136643038", letter_text="dear team"
    )

    assert result.type == SubmissionResultType.FAILED
    assert result.reason is not None and "письмо" in result.reason.lower()
    assert ("click", response.respond_button) not in page.events
    assert ("click", response.respond_no_test_button) not in page.events


async def test_writer_attaches_the_letter_when_no_questions_link_exists_without_a_test() -> (
    None
):
    response = HHRU_SELECTORS.response
    page = _FormStubPage(
        present={response.respond_button, response.respond_no_test_button}
    )
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/136643038", letter_text="dear team"
    )

    assert ("fill", response.letter_textarea) in page.events
    assert ("click", response.respond_button) in page.events
    assert ("click", response.respond_no_test_button) not in page.events
    assert result.type == SubmissionResultType.SUBMITTED


async def test_writer_skips_the_vacancy_when_the_employer_test_is_mandatory() -> None:
    response = HHRU_SELECTORS.response
    page = _FormStubPage(
        present={response.respond_button, response.employer_test_marker}
    )
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/135583370", letter_text="dear team"
    )

    assert result.type == SubmissionResultType.FAILED
    assert result.reason is not None and "тест" in result.reason.lower()
    assert ("click", response.respond_button) not in page.events
    assert ("click", response.respond_no_test_button) not in page.events


class _RelocationStubPage(_StubPage):
    def __init__(self) -> None:
        super().__init__(body_text="")
        self._confirmed = False

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        confirm = HHRU_SELECTORS.response.relocation_confirm
        if selector == confirm and not self._confirmed:
            return object()
        if selector == HHRU_SELECTORS.response.respond_button:
            return object()
        return None

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))
        if selector == HHRU_SELECTORS.response.relocation_confirm:
            self._confirmed = True

    async def text_content(self, selector: str) -> str | None:
        self.events.append(("text", selector))
        if self._confirmed:
            return "Вы откликнулись"
        return "Вы откликаетесь на вакансию в другой стране"


async def test_writer_confirms_cross_country_relocation_warning_and_still_submits() -> (
    None
):
    page = _RelocationStubPage()
    core = _StubCore(page)
    writer = HHRUWriter(
        core=core,  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/999", letter_text="dear team"
    )

    confirm = HHRU_SELECTORS.response.relocation_confirm
    assert ("click", confirm) in page.events
    assert result.type == SubmissionResultType.SUBMITTED


class _PreFormRelocationStubPage(_StubPage):
    def __init__(self) -> None:
        super().__init__(body_text="Вы откликнулись")
        self._confirmed = False

    async def wait_for_selector(
        self, selector: str, timeout: float | None = None
    ) -> Any:
        self.events.append(("wait", selector))
        respond_button = HHRU_SELECTORS.response.respond_button
        if selector == respond_button and not self._confirmed:
            raise RuntimeError("Timeout: response form is blocked by the modal")
        return object()

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        confirm = HHRU_SELECTORS.response.relocation_confirm
        if selector == confirm and not self._confirmed:
            return object()
        if selector == HHRU_SELECTORS.response.respond_button and self._confirmed:
            return object()
        return None

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))
        if selector == HHRU_SELECTORS.response.relocation_confirm:
            self._confirmed = True


async def test_writer_confirms_relocation_modal_that_blocks_the_response_form() -> None:
    page = _PreFormRelocationStubPage()
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/999", letter_text="dear team"
    )

    confirm = HHRU_SELECTORS.response.relocation_confirm
    assert ("click", confirm) in page.events
    assert result.type == SubmissionResultType.SUBMITTED


class _BottomSheetStubPage(_StubPage):
    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        if selector in (
            HHRU_SELECTORS.response.letter_textarea,
            HHRU_SELECTORS.response.respond_button,
        ):
            return object()
        return None

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))
        if selector == HHRU_SELECTORS.response.open_letter_textarea_button:
            raise RuntimeError("Timeout: this form has no cover-letter toggle")


async def test_writer_fills_the_letter_when_the_field_is_already_open() -> None:
    page = _BottomSheetStubPage()
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://hh.ru/vacancy/999", letter_text="dear team"
    )

    response = HHRU_SELECTORS.response
    assert ("click", response.open_letter_textarea_button) not in page.events
    assert ("fill", response.letter_textarea) in page.events
    assert result.type == SubmissionResultType.SUBMITTED


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
    relocation_confirm = HHRU_SELECTORS.response.relocation_confirm
    chat_open = HHRU_SELECTORS.vacancy.chat_open
    open_letter = HHRU_SELECTORS.response.open_letter_textarea_button
    textarea = HHRU_SELECTORS.response.letter_textarea

    assert driving[0] == ("wait", respond_link_top)
    assert driving[1] == ("click", respond_link_top)

    assert driving[2] == (
        "wait",
        f"{relocation_confirm}, {respond_button}, {chat_open}",
    )

    assert driving[3] == ("click", open_letter)
    assert driving[4] == ("wait", textarea)
    assert driving[5] == ("fill", textarea)

    assert driving[6] == ("click", respond_button)

    assert result.type == SubmissionResultType.SUBMITTED
    assert not stub_page.closed


class _FakeChatFrame:
    def __init__(self, sticks: bool = True) -> None:
        self.events: list[tuple[str, str]] = []
        self._values: dict[str, str] = {}
        self._sticks = sticks
        self._sent = False

    async def wait_for_selector(
        self, selector: str, timeout: float | None = None
    ) -> Any:
        self.events.append(("wait", selector))
        return object()

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        return object()

    async def click(self, selector: str, timeout: float | None = None) -> None:
        self.events.append(("click", selector))
        if selector == HHRU_SELECTORS.chat.send_message:
            self._sent = True

    async def fill(
        self, selector: str, text: str, timeout: float | None = None
    ) -> None:
        self.events.append(("fill", selector))
        if self._sticks:
            self._values[selector] = text

    async def input_value(self, selector: str, timeout: float | None = None) -> str:
        self.events.append(("input_value", selector))
        return self._values.get(selector, "")

    async def content(self) -> str:
        letter = self._values.get(HHRU_SELECTORS.chat.letter_input, "")
        return f"<div>{letter}</div>" if self._sent else "<div></div>"


class _ChatStubPage(_StubPage):
    def __init__(self, frame: _FakeChatFrame | None) -> None:
        super().__init__(body_text="")
        self._frame = frame

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        if selector == HHRU_SELECTORS.vacancy.chat_open:
            return object()
        return None

    async def wait_for_frame(
        self, url_marker: str, timeout: float | None = None
    ) -> Any:
        self.events.append(("frame", url_marker))
        return self._frame


async def test_writer_attaches_letter_via_chat_when_the_response_has_no_popup() -> None:
    chat = HHRU_SELECTORS.chat
    frame = _FakeChatFrame(sticks=True)
    page = _ChatStubPage(frame)
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://novosibirsk.hh.ru/vacancy/136883018",
        letter_text="Здравствуйте, меня заинтересовала ваша вакансия",
    )

    assert ("click", HHRU_SELECTORS.vacancy.chat_open) in page.events
    assert ("click", chat.add_cover_letter) in frame.events
    assert ("fill", chat.letter_input) in frame.events
    assert ("click", chat.send_message) in frame.events
    assert result.type == SubmissionResultType.SUBMITTED


async def test_writer_does_not_send_chat_letter_when_the_field_stays_empty() -> None:
    chat = HHRU_SELECTORS.chat
    frame = _FakeChatFrame(sticks=False)
    page = _ChatStubPage(frame)
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://novosibirsk.hh.ru/vacancy/136883018",
        letter_text="dear team",
    )

    assert ("fill", chat.letter_input) in frame.events
    assert ("click", chat.send_message) not in frame.events
    assert result.type == SubmissionResultType.FAILED
    assert result.reason is not None and "письмо" in result.reason.lower()


class _ReloadChatStubPage(_ChatStubPage):
    def __init__(self, frame: _FakeChatFrame | None) -> None:
        super().__init__(frame)
        self._reloaded = False

    async def goto(self, url: str) -> None:
        self.events.append(("goto", url))
        self._reloaded = True

    async def query_selector(self, selector: str) -> Any:
        self.events.append(("query", selector))
        if selector == HHRU_SELECTORS.vacancy.chat_open and self._reloaded:
            return object()
        return None


async def test_writer_reloads_to_reach_the_chat_when_response_is_not_inline() -> None:
    chat = HHRU_SELECTORS.chat
    frame = _FakeChatFrame(sticks=True)
    page = _ReloadChatStubPage(frame)
    url = "https://novosibirsk.hh.ru/vacancy/136883018"
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(vacancy_url=url, letter_text="dear team")

    assert ("goto", url) in page.events
    assert ("click", chat.send_message) in frame.events
    assert result.type == SubmissionResultType.SUBMITTED


async def test_writer_fails_when_the_response_chat_does_not_open() -> None:
    page = _ChatStubPage(None)
    writer = HHRUWriter(
        core=_StubCore(page),  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        timeout=1000,
    )

    result = await writer.submit(
        vacancy_url="https://novosibirsk.hh.ru/vacancy/136883018",
        letter_text="dear team",
    )

    assert result.type == SubmissionResultType.FAILED
    assert result.reason is not None and "чат" in result.reason.lower()
