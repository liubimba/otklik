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
    # /generate is async now: it only transitions the state machine to
    # LETTER_PENDING and returns immediately. AI health is NOT checked
    # here — an unhealthy AI surfaces later when LetterPendingWorker runs
    # the LLM and drives the application into ERROR.
    # NOTE: the old synchronous 409-on-unhealthy coverage is gone; the
    # async error path (worker -> ERROR when no deployments) is not yet
    # covered by a worker-level test. See test_letter_pending_worker.
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 200
    assert response.json()["status"] == "letter_pending"


def test_generate_happy_path_auto_creates_application(
    client: TestClient, ai_layer_with_router: AILayer
):
    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="hello"
    )
    # No pre-call to /queue_for_letter — server auto-creates the Application,
    # fires REGENERATE and lands in LETTER_PENDING. Generation runs async in
    # LetterPendingWorker, so the letter text is NOT in this response; it
    # arrives later via an ApplicationWSEvent.
    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "letter_pending"
    assert body["vacancy_id"] == 1
    assert body["application_id"] > 0
