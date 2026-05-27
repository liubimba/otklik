from fastapi import Response
from fastapi.testclient import TestClient

from headhunter_backend.orchestrator.queue import Orchestrator


def test_resume_unpauses_paused_orchestrator(
    client: TestClient, fake_orchestrator: Orchestrator
) -> None:
    fake_orchestrator.pause()
    assert fake_orchestrator.is_paused() is True

    response: Response = client.post("/api/v1/orchestrator/resume")

    assert response.status_code == 200
    assert fake_orchestrator.is_paused() is False


def test_resume_is_idempotent_when_not_paused(
    client: TestClient, fake_orchestrator: Orchestrator
) -> None:
    assert fake_orchestrator.is_paused() is False

    response: Response = client.post("/api/v1/orchestrator/resume")

    assert response.status_code == 200
    assert fake_orchestrator.is_paused() is False
