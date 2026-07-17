from fastapi import Response
from fastapi.testclient import TestClient

from otklik_backend.secrets.store import SecretStorageMode
from tests.conftest import FakeSecretStore


def test_health_answers_without_any_dependency(client: TestClient) -> None:
    response: Response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_secret_storage_reports_the_injected_fakes_mode(
    client: TestClient, fake_secret_store: FakeSecretStore
) -> None:
    response: Response = client.get("/api/v1/system/secret-storage")
    assert response.status_code == 200
    assert response.json() == {"mode": fake_secret_store.mode.value}


def test_secret_storage_reports_file_mode(client: TestClient) -> None:
    from otklik_backend.api.app import app
    from otklik_backend.api.dependencies import get_secret_store

    file_mode_store = FakeSecretStore(mode=SecretStorageMode.FILE)
    app.dependency_overrides[get_secret_store] = lambda: file_mode_store
    try:
        response: Response = client.get("/api/v1/system/secret-storage")
    finally:
        del app.dependency_overrides[get_secret_store]

    assert response.status_code == 200
    assert response.json() == {"mode": "file"}
