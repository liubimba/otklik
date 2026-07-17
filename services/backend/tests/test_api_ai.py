from fastapi import Response
from fastapi.testclient import TestClient

from otklik_backend.ai.layer import AILayer

from tests.test_ai import _fake_model_response


def test_ai_health_no_deployments(client: TestClient, ai_layer_with_router: AILayer):
    ai_layer_with_router._deployments = []
    response: Response = client.get("/api/v1/system/ai/health")
    assert response.status_code == 200
    assert response.json() == {"status": "no_deployments"}


def test_ai_health_healthy(client: TestClient, ai_layer_with_router: AILayer):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )
    response: Response = client.get("/api/v1/system/ai/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_generate_404_when_vacancy_missing(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )
    response: Response = client.post("/api/v1/vacancies/9999/application/generate")
    assert response.status_code == 404


def test_generate_returns_pending_even_when_ai_unhealthy(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._deployments = []
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 200
    assert response.json()["status"] == "letter_pending"


def test_generate_happy_path_auto_creates_application(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="hello"
    )
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "letter_pending"
    assert body["vacancy_id"] == 1
    assert body["application_id"] > 0
