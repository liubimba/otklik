from collections.abc import AsyncIterator

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.sites.kwork.parser import KworkParser

PAGE = """
<html><body><script>
window.stateData = {"pagination":{"total":2},"wants":[
  {"id":111,"name":"Создание баннера","description":"Нужен баннер для студии",
   "priceLimit":500.00,"possiblePriceLimit":1500,"isHigherPrice":true,
   "user":{"USERID":1,"username":"natasha"}},
  {"id":222,"name":"Правка сайта","description":"Поправить вёрстку",
   "priceLimit":1000.00,"possiblePriceLimit":1000,
   "user":{"username":"ivan"}},
  {"id":333,"name":"","description":"без названия","priceLimit":10}
]};
</script></body></html>
"""

EMPTY = "<html><body>no data here</body></html>"


class FakePage:
    def __init__(self, html: str) -> None:
        self._html = html

    def get_url(self) -> str:
        return "https://kwork.ru/projects"

    async def content(self) -> str:
        return self._html


def _parser() -> KworkParser:
    return KworkParser(core=None)  # type: ignore[arg-type]


async def _collect(it: AsyncIterator[VacancyAPISchema]) -> list[VacancyAPISchema]:
    return [item async for item in it]


async def test_parses_projects_from_the_embedded_state() -> None:
    vacancies = await _collect(_parser().parse(FakePage(PAGE)))  # type: ignore[arg-type]

    assert [v.title for v in vacancies] == ["Создание баннера", "Правка сайта"]
    first = vacancies[0]
    assert first.apply_link == "https://kwork.ru/projects/111"
    assert first.description == "Нужен баннер для студии"
    assert first.company_name == "natasha"
    assert first.salary == "500–1500 ₽"


async def test_budget_without_a_higher_bound_reads_as_a_ceiling() -> None:
    vacancies = await _collect(_parser().parse(FakePage(PAGE)))  # type: ignore[arg-type]
    assert vacancies[1].salary == "до 1000 ₽"
    assert vacancies[1].company_name == "ivan"


async def test_a_project_without_a_title_is_skipped() -> None:
    vacancies = await _collect(_parser().parse(FakePage(PAGE)))  # type: ignore[arg-type]
    assert all(v.title for v in vacancies)
    assert "https://kwork.ru/projects/333" not in {v.apply_link for v in vacancies}


async def test_a_page_without_project_data_yields_nothing() -> None:
    assert await _collect(_parser().parse(FakePage(EMPTY))) == []  # type: ignore[arg-type]
