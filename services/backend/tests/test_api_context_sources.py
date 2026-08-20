import httpx
from fastapi import Response
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.api.app import app
from otklik_backend.api.dependencies import get_context_source_service
from otklik_backend.core.context_source import ContextSourceStatus
from otklik_backend.secrets.store import SecretStorageMode
from otklik_backend.sources.fetchers import SourceFetcherRegistry
from otklik_backend.sources.service import ContextSourceService


def _mock_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, html="<html><body>Fake page content</body></html>")


class _OfflineSecretStore:
    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    @property
    def mode(self) -> SecretStorageMode:
        return SecretStorageMode.FILE

    async def get(self, account: str) -> str | None:
        return self.items.get(account)

    async def set(self, account: str, secret: str) -> None:
        self.items[account] = secret

    async def delete(self, account: str) -> None:
        self.items.pop(account, None)


def _make_offline_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> ContextSourceService:
    transport = httpx.MockTransport(_mock_handler)
    client = httpx.AsyncClient(transport=transport)
    registry = SourceFetcherRegistry(client=client)
    return ContextSourceService(
        session_maker=session_factory,
        registry=registry,
        secret_store=_OfflineSecretStore(),  # type: ignore[arg-type]
    )


async def test_post_creates_context_source_without_content_field(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        response: Response = client.post(
            "/api/v1/context-sources",
            json={
                "label": "My blog",
                "url": "https://example.com/blog",
                "description": None,
            },
        )
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] in (
        ContextSourceStatus.OK.value,
        ContextSourceStatus.ERROR.value,
    )
    assert "content" not in body


async def test_get_lists_created_context_source(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        client.post(
            "/api/v1/context-sources",
            json={
                "label": "My blog",
                "url": "https://example.com/blog",
                "description": None,
            },
        )
        response: Response = client.get("/api/v1/context-sources")
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["label"] == "My blog"


async def test_refresh_single_source_returns_200(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        created = client.post(
            "/api/v1/context-sources",
            json={
                "label": "My blog",
                "url": "https://example.com/blog",
                "description": None,
            },
        ).json()
        response: Response = client.post(
            f"/api/v1/context-sources/{created['id']}/refresh"
        )
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == ContextSourceStatus.OK.value


async def test_refresh_unknown_source_returns_404(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        response: Response = client.post("/api/v1/context-sources/999/refresh")
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 404


async def test_refresh_all_returns_refreshed_count(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        client.post(
            "/api/v1/context-sources",
            json={"label": "One", "url": "https://example.com/1", "description": None},
        )
        client.post(
            "/api/v1/context-sources",
            json={"label": "Two", "url": "https://example.com/2", "description": None},
        )
        response: Response = client.post("/api/v1/context-sources/refresh")
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 200
    assert response.json() == {"refreshed": 2}


async def test_patch_unknown_source_returns_404(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        response: Response = client.patch(
            "/api/v1/context-sources/999",
            json={
                "label": "Renamed",
                "url": "https://example.com/renamed",
                "description": None,
            },
        )
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert response.status_code == 404


async def test_delete_removes_source_and_get_no_longer_lists_it(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service = _make_offline_service(session_factory)
    app.dependency_overrides[get_context_source_service] = lambda: service
    try:
        created = client.post(
            "/api/v1/context-sources",
            json={
                "label": "My blog",
                "url": "https://example.com/blog",
                "description": None,
            },
        ).json()
        delete_response: Response = client.delete(
            f"/api/v1/context-sources/{created['id']}"
        )
        list_response: Response = client.get("/api/v1/context-sources")
    finally:
        app.dependency_overrides.pop(get_context_source_service, None)

    assert delete_response.status_code == 204
    assert list_response.json() == []
