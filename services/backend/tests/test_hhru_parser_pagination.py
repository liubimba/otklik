from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.sites.hh_ru.parser import HHRUParser
from otklik_backend.sites.hh_ru.selectors import HHRU_SELECTORS

SERP_HTML = (
    '<a data-qa="serp-item__title" href="https://hh.ru/vacancy/1">A</a>'
    '<a data-qa="serp-item__title" href="https://hh.ru/vacancy/2">B</a>'
)
VACANCY_HTML = "<div><h1>x</h1></div>"
VACANCY_HTML_RESPONDED = (
    '<div><h1>x</h1><a data-qa="vacancy-response-link-view-topic">Чат</a></div>'
)


class FakeElement:
    def __init__(self, text: str) -> None:
        self._text = text

    async def text_content(self) -> str:
        return self._text


class FakeVacancyPage:
    def __init__(self, content_html: str = VACANCY_HTML) -> None:
        self._content_html = content_html

    async def set_viewport_size(self, width: int, height: int) -> None:
        pass

    async def goto(self, url: str) -> None:
        pass

    async def wait_for_selector(self, selector: str, timeout: int = 0) -> FakeElement:
        return FakeElement("value")

    async def content(self) -> str:
        return self._content_html

    async def close(self) -> None:
        pass


class FakeSearchPage:
    def __init__(self) -> None:
        self.content_reads = 0

    def get_url(self) -> str:
        return "https://hh.ru/search/vacancy?text=python"

    async def content(self) -> str:
        self.content_reads += 1
        if self.content_reads > 1:
            raise RuntimeError(
                "search page re-read — parse() must drain one page and return; "
                "pagination is the caller's job"
            )
        return SERP_HTML

    async def close(self) -> None:
        pass


class FakeCore:
    def __init__(self, vacancy_html: str = VACANCY_HTML) -> None:
        self._page = FakeVacancyPage(vacancy_html)

    async def open_reusable_page(self, key: str, url: str) -> FakeVacancyPage:
        await self._page.goto(url)
        return self._page


async def test_parse_drains_one_page_and_terminates() -> None:
    parser = HHRUParser(core=FakeCore(), selectors=HHRU_SELECTORS)  # type: ignore[arg-type]
    parser._delay_sec = 0
    parser._jitter_ms = 0

    search_page = FakeSearchPage()
    vacancies: list[VacancyAPISchema] = []
    async for vacancy in parser.parse(search_page=search_page):  # type: ignore[arg-type]
        vacancies.append(vacancy)

    assert search_page.content_reads == 1
    assert [v.apply_link for v in vacancies] == [
        "https://hh.ru/vacancy/1",
        "https://hh.ru/vacancy/2",
    ]
    assert all(v.already_responded is False for v in vacancies)


async def test_parse_flags_already_responded_vacancies() -> None:
    parser = HHRUParser(core=FakeCore(VACANCY_HTML_RESPONDED), selectors=HHRU_SELECTORS)  # type: ignore[arg-type]
    parser._delay_sec = 0
    parser._jitter_ms = 0

    vacancies: list[VacancyAPISchema] = []
    async for vacancy in parser.parse(search_page=FakeSearchPage()):  # type: ignore[arg-type]
        vacancies.append(vacancy)

    assert len(vacancies) == 2
    assert all(v.already_responded is True for v in vacancies)
