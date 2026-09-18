from collections.abc import AsyncIterator

from otklik_backend.api.schemas import EmploymentType, VacancyAPISchema, WorkFormat
from otklik_backend.sites.habr.parser import HabrParser

SEARCH_HTML = """
<div class="vacancies">
  <div class="vacancy-card">
    <a class="vacancy-card__title-link" href="/vacancies/1001">Backend-разработчик</a>
  </div>
  <div class="vacancy-card">
    <a class="vacancy-card__title-link" href="/vacancies/1002">Frontend-разработчик</a>
  </div>
  <div class="vacancy-card">
    <a class="vacancy-card__title-link" href="/vacancies/1001">Backend-разработчик</a>
  </div>
</div>
"""

DETAIL_HTML = """
<h1 class="page-title__title">Backend-разработчик</h1>
<div class="company_name"><a href="/companies/acme">ACME</a></div>
<div class="basic-salary">от 250 000 ₽</div>
<div class="vacancy-description__text">Пишем сервисы на Python.</div>
<div class="content-section">
  <div class="content-section__title">Требования</div>Python, PostgreSQL
</div>
<div class="content-section">
  <div class="content-section__title">Условия</div>Можно удалённо · Санкт-Петербург · Неполный рабочий день
</div>
"""

DETAIL_NO_DESCRIPTION = """
<h1 class="page-title__title">Без описания</h1>
"""


class FakeBrowserPage:
    def __init__(self, url: str, html: str) -> None:
        self._url = url
        self._html = html

    def get_url(self) -> str:
        return self._url

    async def content(self) -> str:
        return self._html


class FakeBrowserCore:
    def __init__(self, details: dict[str, str]) -> None:
        self._details = details
        self.opened: list[str] = []

    async def open_reusable_page(self, key: str, url: str) -> FakeBrowserPage | None:
        self.opened.append(url)
        html = self._details.get(url)
        return FakeBrowserPage(url, html) if html is not None else None


def _make_parser(details: dict[str, str]) -> tuple[HabrParser, FakeBrowserCore]:
    core = FakeBrowserCore(details)
    return HabrParser(core=core), core  # type: ignore[arg-type]


async def _collect(it: AsyncIterator[VacancyAPISchema]) -> list[VacancyAPISchema]:
    return [item async for item in it]


def test_parse_detail_extracts_every_field() -> None:
    parser, _ = _make_parser({})
    vacancy = parser._parse_detail(
        DETAIL_HTML, "https://career.habr.com/vacancies/1001"
    )
    assert vacancy is not None
    assert vacancy.title == "Backend-разработчик"
    assert vacancy.apply_link == "https://career.habr.com/vacancies/1001"
    assert vacancy.description == "Пишем сервисы на Python."
    assert vacancy.company_name == "ACME"
    assert vacancy.salary == "от 250 000 ₽"
    assert vacancy.work_formats == [WorkFormat.REMOTE]
    assert vacancy.employment_types == [EmploymentType.PART_TIME]


def test_parse_detail_skips_a_vacancy_without_a_description() -> None:
    parser, _ = _make_parser({})
    assert (
        parser._parse_detail(DETAIL_NO_DESCRIPTION, "https://career.habr.com/x") is None
    )


def test_relative_hrefs_resolve_to_absolute_career_habr_urls() -> None:
    parser, _ = _make_parser({})
    assert (
        parser._resolve_href("/vacancies/42") == "https://career.habr.com/vacancies/42"
    )
    assert (
        parser._resolve_href("https://career.habr.com/vacancies/42")
        == "https://career.habr.com/vacancies/42"
    )


async def test_parse_opens_each_unique_vacancy_and_yields_it() -> None:
    details = {
        "https://career.habr.com/vacancies/1001": DETAIL_HTML,
        "https://career.habr.com/vacancies/1002": DETAIL_HTML.replace(
            "Backend-разработчик", "Frontend-разработчик"
        ),
    }
    parser, core = _make_parser(details)
    search_page = FakeBrowserPage("https://career.habr.com/vacancies", SEARCH_HTML)

    vacancies = await _collect(parser.parse(search_page))  # type: ignore[arg-type]

    assert [v.title for v in vacancies] == [
        "Backend-разработчик",
        "Frontend-разработчик",
    ]
    assert core.opened == [
        "https://career.habr.com/vacancies/1001",
        "https://career.habr.com/vacancies/1002",
    ]
