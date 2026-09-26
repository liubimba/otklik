from typing import Any

from otklik_backend.api.schemas import EmploymentType, VacancyAPISchema, WorkFormat
from otklik_backend.sites.hirify.parser import HirifyParser


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeClient:
    def __init__(
        self, list_payload: dict[str, Any], details: dict[str, dict[str, Any]]
    ) -> None:
        self._list_payload = list_payload
        self._details = details
        self.urls: list[str] = []

    async def get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> FakeResponse:
        self.urls.append(url)
        marker = "/api/vacancies/"
        if marker in url:
            vacancy_id = url.split(marker, 1)[1]
            return FakeResponse({"data": self._details.get(vacancy_id, {})})
        return FakeResponse(self._list_payload)


class FakePage:
    def __init__(self, url: str) -> None:
        self._url = url

    def get_url(self) -> str:
        return self._url


def _parser(client: FakeClient) -> HirifyParser:
    parser = HirifyParser(core=None, client=client)  # type: ignore[arg-type]
    parser._delay_sec = 0
    parser._jitter_ms = 0
    return parser


async def _collect(parser: HirifyParser, url: str) -> list[VacancyAPISchema]:
    return [v async for v in parser.parse(FakePage(url))]  # type: ignore[arg-type]


def test_to_api_url_forwards_the_query_to_the_api_host() -> None:
    parser = HirifyParser(core=None)  # type: ignore[arg-type]
    assert (
        parser._to_api_url("https://hirify.me/vacancies?page=2&grades=5")
        == "https://api.hirify.me/api/vacancies?page=2&grades=5"
    )


async def test_parse_maps_a_vacancy_from_list_and_detail() -> None:
    client = FakeClient(
        list_payload={
            "data": [
                {
                    "id": "1164753",
                    "slug": "1164753-lead-network-engineer",
                    "title": "Ведущий инженер",
                    "company_title": "NDA",
                    "work_format": ["onsite"],
                    "work_type": "fulltime",
                    "grades": [{"id": 5, "name": "lead"}],
                    "salary": None,
                    "has_applied": True,
                }
            ]
        },
        details={
            "1164753": {"text": "<p>Админировать сеть</p><h3>Компания</h3>"},
        },
    )
    vacancies = await _collect(_parser(client), "https://hirify.me/vacancies?page=1")

    assert len(vacancies) == 1
    vacancy = vacancies[0]
    assert vacancy.title == "Ведущий инженер"
    assert vacancy.apply_link == "https://hirify.me/jobs/1164753-lead-network-engineer"
    assert "Админировать сеть" in vacancy.description
    assert "<p>" not in vacancy.description
    assert vacancy.company_name is None
    assert vacancy.work_formats == [WorkFormat.ONSITE]
    assert vacancy.employment_types == [EmploymentType.FULL_TIME]
    assert vacancy.work_experience == "lead"
    assert vacancy.already_responded is True


async def test_parse_skips_a_vacancy_without_a_description() -> None:
    client = FakeClient(
        list_payload={
            "data": [
                {"id": "1", "slug": "1-x", "title": "No text"},
            ]
        },
        details={"1": {"text": ""}},
    )
    assert await _collect(_parser(client), "https://hirify.me/vacancies") == []


async def test_parse_keeps_a_named_company_and_maps_remote_parttime() -> None:
    client = FakeClient(
        list_payload={
            "data": [
                {
                    "id": "2",
                    "slug": "2-remote-dev",
                    "title": "Backend Dev",
                    "company_title": "Acme",
                    "work_format": ["remote"],
                    "work_type": "parttime",
                }
            ]
        },
        details={"2": {"text": "<div>Build services</div>"}},
    )
    vacancy = (await _collect(_parser(client), "https://hirify.me/vacancies"))[0]
    assert vacancy.company_name == "Acme"
    assert vacancy.work_formats == [WorkFormat.REMOTE]
    assert vacancy.employment_types == [EmploymentType.PART_TIME]
