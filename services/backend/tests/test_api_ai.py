from fastapi import Response
from fastapi.testclient import TestClient
from headhunter_backend.ai.layer import AILayer

from tests.test_ai import _fake_model_response


def test_ai_health_no_deployments(client: TestClient, ai_layer_with_router: AILayer):
    ai_layer_with_router._deployments = []
    response: Response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    assert response.json() == {"status": "no_deployments"}


def test_ai_health_healthy(client: TestClient, ai_layer_with_router: AILayer):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )
    response: Response = client.get("/api/v1/ai/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_cover_letter_404_when_vacancy_missing(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )
    response: Response = client.post("/api/v1/ai/create_cover_letter/9999")
    assert response.status_code == 404


def test_create_cover_letter_409_when_no_application(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="pong"
    )
    response: Response = client.post("/api/v1/ai/create_cover_letter/1")
    assert response.status_code == 409


def test_create_cover_letter_409_when_not_ready(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._deployments = []
    response: Response = client.post("/api/v1/ai/create_cover_letter/1")
    assert response.status_code == 409


def test_create_cover_letter_happy_path(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="hello"
    )
    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 200
    response: Response = client.post("/api/v1/ai/create_cover_letter/1")
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "hello"
    assert body["model_used"] == "test-model"
