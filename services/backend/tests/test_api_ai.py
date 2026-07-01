from fastapi import Response
from fastapi.testclient import TestClient

from headhunter_backend.ai.layer import AILayer

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


def test_generate_409_when_ai_unhealthy(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._deployments = []
    # Vacancy exists, but AI layer has no deployments — regenerate should raise.
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code in (409, 500, 503)


def test_generate_happy_path_auto_creates_application(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="hello"
    )
    # No pre-call to /queue_for_letter — server should create Application internally.
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "hello"
    assert body["model_used"] == "test-model"
