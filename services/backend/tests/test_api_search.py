from fastapi.testclient import TestClient
from pydantic import HttpUrl

from headhunter_backend.api.schemas import VacanciesStartSearchRequestAPISchema
from tests.conftest import FakeSearchService


def _body(url: str = "https://hh.ru/search/vacancy") -> dict[str, object]:
    return VacanciesStartSearchRequestAPISchema(url=HttpUrl(url)).model_dump(
        mode="json"
    )


def test_post_parse_returns_search_id(client: TestClient) -> None:
    response = client.post("/api/v1/search/parse/start", json=_body())
    assert response.status_code == 200
    payload = response.json()
    assert "search_id" in payload
    assert isinstance(payload["search_id"], str)


def test_second_post_parse_returns_409(client: TestClient) -> None:
    first = client.post("/api/v1/search/parse/start", json=_body())
    assert first.status_code == 200

    second = client.post("/api/v1/search/parse/start", json=_body())
    assert second.status_code == 409


def test_delete_parse_unknown_id_returns_404(client: TestClient) -> None:
    response = client.delete("/api/v1/search/parse/no-such-id")
    assert response.status_code == 404


def test_delete_parse_existing_id_cancels_and_returns_ok(
    client: TestClient,
    fake_search_service: FakeSearchService,
) -> None:
    posted = client.post("/api/v1/search/parse/start", json=_body())
    search_id = posted.json()["search_id"]

    response = client.delete(f"/api/v1/search/parse/{search_id}")
    assert response.status_code in (200, 204)
    assert search_id not in fake_search_service._queue
