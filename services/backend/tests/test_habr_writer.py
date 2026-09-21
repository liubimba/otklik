from otklik_backend.core.site.result import SubmissionResultType
from otklik_backend.sites.habr.writer import (
    RESPOND_BUTTON_MISSING,
    HabrWriter,
)


class FakePage:
    def __init__(self) -> None:
        self.present: set[str] = set()
        self.clickable: set[str] = set()
        self.clicks: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self._reveal_on_click: dict[str, set[str]] = {}

    def reveal_after_click(self, click_substr: str, reveal: set[str]) -> None:
        self._reveal_on_click[click_substr] = reveal

    def _has(self, selector: str) -> bool:
        return any(marker in selector for marker in self.present)

    async def query_selector(self, selector: str) -> object | None:
        return object() if self._has(selector) else None

    async def wait_for_selector(
        self, selector: str, timeout: float | None = None
    ) -> object:
        if self._has(selector):
            return object()
        raise TimeoutError(f"not found: {selector}")

    async def click_first_visible(
        self, selector: str, timeout: float | None = None
    ) -> bool:
        for marker in self.clickable:
            if marker in selector:
                self.clicks.append(marker)
                self.present |= self._reveal_on_click.get(marker, set())
                return True
        return False

    async def click(self, selector: str, timeout: float | None = None) -> None:
        for marker in self.clickable:
            if marker in selector:
                self.clicks.append(marker)
                self.present |= self._reveal_on_click.get(marker, set())
                return
        raise TimeoutError(f"not clickable: {selector}")

    async def fill(
        self, selector: str, text: str, timeout: float | None = None
    ) -> None:
        self.fills.append((selector, text))


class FakeCore:
    def __init__(self, page: FakePage) -> None:
        self._page = page

    async def open_reusable_page(self, key: str, url: str) -> FakePage:
        return self._page


def _writer(page: FakePage) -> HabrWriter:
    return HabrWriter(core=FakeCore(page), min_delay_ms=0, jitter_delay_ms=0)  # type: ignore[arg-type]


async def test_responds_then_attaches_the_cover_letter() -> None:
    page = FakePage()
    page.clickable = {"Откликнуться", "Дополнить отклик"}
    page.reveal_after_click(
        "Откликнуться",
        {"action-result-box--appearance-success", 'textarea[name="body"]'},
    )

    result = await _writer(page).submit(
        "https://career.habr.com/vacancies/1", "Моё письмо"
    )

    assert result.type is SubmissionResultType.SUBMITTED
    assert page.clicks == ["Откликнуться", "Дополнить отклик"]
    assert page.fills == [('textarea[name="body"]', "Моё письмо")]


async def test_already_responded_vacancy_gets_its_letter_edited_in() -> None:
    page = FakePage()
    page.present = {".vacancy-response-section"}
    page.clickable = {"#create-vacancy-response", "Редактировать", "Сохранить"}
    page.reveal_after_click("Редактировать", {'textarea[name="body"]'})

    result = await _writer(page).submit("https://career.habr.com/vacancies/2", "Письмо")

    assert result.type is SubmissionResultType.SUBMITTED
    assert "Откликнуться" not in page.clicks
    assert "Редактировать" in page.clicks
    assert "Сохранить" in page.clicks
    assert page.fills == [('textarea[name="body"]', "Письмо")]


async def test_missing_respond_button_fails_without_sending() -> None:
    page = FakePage()

    result = await _writer(page).submit("https://career.habr.com/vacancies/3", "letter")

    assert result.type is SubmissionResultType.FAILED
    assert result.reason == RESPOND_BUTTON_MISSING
    assert page.fills == []


async def test_response_still_submitted_when_letter_cannot_attach() -> None:
    page = FakePage()
    page.clickable = {"Откликнуться"}
    page.reveal_after_click("Откликнуться", {"action-result-box--appearance-success"})

    result = await _writer(page).submit("https://career.habr.com/vacancies/4", "letter")

    assert result.type is SubmissionResultType.SUBMITTED
    assert page.clicks == ["Откликнуться"]
    assert page.fills == []
