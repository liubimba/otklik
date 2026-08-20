import httpx
from fastapi import Response
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.api.app import app
from otklik_backend.api.dependencies import get_context_source_service, get_secret_store
from otklik_backend.core.context_source import ContextSourceStatus
from otklik_backend.secrets.store import SecretStorageMode, context_source_account_for
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
    store: _OfflineSecretStore | None = None,
) -> ContextSourceService:
    transport = httpx.MockTransport(_mock_handler)
    client = httpx.AsyncClient(transport=transport)
    registry = SourceFetcherRegistry(client=client)
    return ContextSourceService(
        session_maker=session_factory,
        registry=registry,
        secret_store=store or _OfflineSecretStore(),  # type: ignore[arg-type]
    )


def _override_with_store(
    store: _OfflineSecretStore, service: ContextSourceService
) -> None:
    app.dependency_overrides[get_context_source_service] = lambda: service
    app.dependency_overrides[get_secret_store] = lambda: store


def _clear_overrides() -> None:
    app.dependency_overrides.pop(get_context_source_service, None)
    app.dependency_overrides.pop(get_secret_store, None)


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
                "kind": "web",
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
                "kind": "web",
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
                "kind": "web",
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
            json={
                "label": "One",
                "kind": "web",
                "url": "https://example.com/1",
                "description": None,
            },
        )
        client.post(
            "/api/v1/context-sources",
            json={
                "label": "Two",
                "kind": "web",
                "url": "https://example.com/2",
                "description": None,
            },
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
                "kind": "web",
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
                "kind": "web",
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


async def test_post_youtrack_with_token_returns_has_token_true_no_token_leak(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        response: Response = client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "token": "secret-token",
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 201
    body = response.json()
    assert body["has_token"] is True
    assert "token" not in body
    assert "content" not in body
    assert body["config"] == {
        "base_url": "https://yt.example.com",
        "query": "project: X",
    }
    assert store.items[context_source_account_for(body["id"])] == "secret-token"


async def test_post_youtrack_without_token_returns_422(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        response: Response = client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 422


async def test_get_lists_youtrack_source_with_has_token_true(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "token": "secret-token",
            },
        )
        response: Response = client.get("/api/v1/context-sources")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["has_token"] is True


async def test_patch_clear_token_returns_has_token_false(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        created = client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "token": "secret-token",
            },
        ).json()
        response: Response = client.patch(
            f"/api/v1/context-sources/{created['id']}",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "clear_token": True,
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["has_token"] is False
    assert context_source_account_for(created["id"]) not in store.items


async def test_patch_changing_kind_returns_409(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        created = client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "token": "secret-token",
            },
        ).json()
        response: Response = client.patch(
            f"/api/v1/context-sources/{created['id']}",
            json={
                "label": "YouTrack",
                "kind": "web",
                "url": "https://example.com/other",
                "description": None,
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 409
    assert response.json()["detail"] == "kind is immutable"


async def test_patch_replaces_config_keeps_kind(
    client, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    store = _OfflineSecretStore()
    service = _make_offline_service(session_factory, store)
    _override_with_store(store, service)
    try:
        created = client.post(
            "/api/v1/context-sources",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: X"},
                "token": "secret-token",
            },
        ).json()
        response: Response = client.patch(
            f"/api/v1/context-sources/{created['id']}",
            json={
                "label": "YouTrack",
                "kind": "youtrack",
                "config": {"base_url": "https://yt.example.com", "query": "project: Y"},
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "youtrack"
    assert body["config"] == {
        "base_url": "https://yt.example.com",
        "query": "project: Y",
    }
