from fastapi import Response
from fastapi.testclient import TestClient

from otklik_backend.api.schemas import OrchestratorStatusAPISchema
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker


def test_resume_unpauses_paused_orchestrator(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    fake_orchestrator.pause()
    assert fake_orchestrator.is_paused() is True

    response: Response = client.post("/api/v1/system/orchestrator/resume")

    assert response.status_code == 200
    assert fake_orchestrator.is_paused() is False


def test_resume_is_idempotent_when_not_paused(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    assert fake_orchestrator.is_paused() is False

    response: Response = client.post("/api/v1/system/orchestrator/resume")

    assert response.status_code == 200
    assert fake_orchestrator.is_paused() is False


def test_status_default(client: TestClient) -> None:
    response: Response = client.get("/api/v1/system/orchestrator/status")
    assert response.status_code == 200
    payload = OrchestratorStatusAPISchema.model_validate(response.json())
    assert payload.paused is False
    assert payload.reason is None
    assert payload.queue_size == 0
    assert list(payload.queue) == []


def test_status_paused_with_reason(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    fake_orchestrator.pause(reason="captcha")
    response: Response = client.get("/api/v1/system/orchestrator/status")
    payload = OrchestratorStatusAPISchema.model_validate(response.json())
    assert payload.paused is True
    assert payload.reason == "captcha"


def test_status_reason_cleared_on_resume(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    fake_orchestrator.pause(reason="captcha")
    fake_orchestrator.resume()
    response: Response = client.get("/api/v1/system/orchestrator/status")
    payload = OrchestratorStatusAPISchema.model_validate(response.json())
    assert payload.paused is False
    assert payload.reason is None


async def test_status_queue_contents(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    await fake_orchestrator.enqueue(application_id=11)
    await fake_orchestrator.enqueue(application_id=22)
    response: Response = client.get("/api/v1/system/orchestrator/status")
    payload = OrchestratorStatusAPISchema.model_validate(response.json())
    assert payload.queue_size == 2
    assert list(payload.queue) == [11, 22]


def test_resume_clears_pause_reason(
    client: TestClient, fake_orchestrator: LetterSendingWorker
) -> None:
    fake_orchestrator.pause(reason="captcha")
    assert fake_orchestrator.get_pause_reason() == "captcha"
    client.post("/api/v1/system/orchestrator/resume")
    assert fake_orchestrator.get_pause_reason() is None
