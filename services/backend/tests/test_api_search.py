from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from headhunter_backend.api.schemas import (
    SearchHistoryAPISchema,
    SearchStatusAPISchema,
    VacanciesStartSearchRequestAPISchema,
)
from headhunter_backend.db.models import SearchHistoryORM
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


def test_get_history_empty_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/v1/search/history")
    assert response.status_code == 200
    assert response.json() == []


@pytest.fixture
async def seeded_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Two finished runs with explicit, distinct started_at so the
    newest-first ordering is deterministic."""
    base = datetime(2026, 1, 1, 12, 0, 0)
    async with session_factory() as session:
        session.add(
            SearchHistoryORM(
                id="older",
                url="https://hh.ru/search/vacancy?text=older",
                max_vacancies=10,
                max_pages=2,
                status=SearchStatusAPISchema.FINISHED,
                parsed_vacancies=7,
                parsed_pages=2,
                started_at=base,
            )
        )
        session.add(
            SearchHistoryORM(
                id="newer",
                url="https://hh.ru/search/vacancy?text=newer",
                max_vacancies=20,
                max_pages=3,
                status=SearchStatusAPISchema.FAILED,
                parsed_vacancies=3,
                parsed_pages=1,
                started_at=base + timedelta(hours=1),
                error="boom",
            )
        )
        await session.commit()


def test_get_history_returns_rows_newest_first(
    client: TestClient,
    seeded_history: None,
) -> None:
    response = client.get("/api/v1/search/history")
    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == ["newer", "older"]
    # Every row conforms to the response contract.
    for item in payload:
        SearchHistoryAPISchema.model_validate(item)
    assert payload[0]["error"] == "boom"
    assert payload[0]["status"] == "failed"
