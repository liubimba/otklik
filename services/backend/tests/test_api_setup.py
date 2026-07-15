from collections.abc import AsyncIterator

from fastapi import Response

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.api.app import app
from otklik_backend.api.dependencies import get_ollama_gate
from otklik_backend.api.schemas import SettingsAPISchema
from otklik_backend.setup.ollama import OllamaPullError, PullProgress


class _FailingPullOllamaGate:
    """Отдаёт пару кадров прогресса, а потом падает — как реальная Ollama,
    у которой на середине загрузки кончилось место на диске."""

    async def pull(self) -> AsyncIterator[PullProgress]:
        yield PullProgress(
            status="downloading", completed_bytes=1, total_bytes=2, percent=50.0
        )
        yield PullProgress(
            status="downloading", completed_bytes=2, total_bytes=4, percent=50.0
        )
        raise OllamaPullError("no space left on device")


def test_setup_state(client):
    response: Response = client.get("/api/v1/setup/state")
    assert response.status_code == 200
    payload = response.json()
    assert payload["hardware"]["tier"] in {"capable", "weak"}
    assert payload["ollama"] == "ready"  # FakeOllamaGate из conftest
    assert payload["has_deployment"] is False
    assert payload["local_model"] == "ollama_chat/qwen2.5:7b"
    assert payload["cloud_model"] == "gigachat/GigaChat-2"


def test_setup_benchmark(client):
    response: Response = client.post("/api/v1/setup/benchmark")
    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is True
    assert payload["letter"]


def test_setup_pull_streams_progress(client):
    with client.stream("POST", "/api/v1/setup/pull") as response:
        assert response.status_code == 200
        frames = [line for line in response.iter_lines() if line.startswith("data:")]
    assert len(frames) >= 2
    assert '"percent"' in frames[0]


def test_setup_pull_delivers_failure_in_band(client):
    """Ответ уже ушёл со статусом 200 к моменту, когда Ollama падает
    (нет места на диске) — единственный способ сказать фронтенду об этом
    без обрыва соединения — кадр ошибки внутри того же стрима."""
    app.dependency_overrides[get_ollama_gate] = lambda: _FailingPullOllamaGate()
    try:
        with client.stream("POST", "/api/v1/setup/pull") as response:
            assert response.status_code == 200
            frames = [
                line for line in response.iter_lines() if line.startswith("data:")
            ]
        # Соединение должно закрыться штатно (iter_lines завершается без
        # исключения), а не оборваться на середине.
    finally:
        del app.dependency_overrides[get_ollama_gate]

    assert len(frames) == 3
    assert '"percent"' in frames[0]
    assert '"percent"' in frames[1]
    assert '"type": "error"' in frames[2]
    assert "no space left on device" in frames[2]


def test_setup_deployment_writes_settings(client):
    body = LLMDeployment(
        model="ollama_chat/qwen2.5:7b", api_base="http://localhost:11434"
    ).model_dump()
    response: Response = client.post("/api/v1/setup/deployment", json=body)
    assert response.status_code == 200
    settings = SettingsAPISchema.model_validate(response.json())
    assert len(settings.llm.deployments) == 1
    assert settings.llm.deployments[0].model == "ollama_chat/qwen2.5:7b"

    state = client.get("/api/v1/setup/state").json()
    assert state["has_deployment"] is True


def test_setup_deployment_is_idempotent(client):
    body = LLMDeployment(
        model="ollama_chat/qwen2.5:7b", api_base="http://localhost:11434"
    ).model_dump()
    client.post("/api/v1/setup/deployment", json=body)
    response: Response = client.post("/api/v1/setup/deployment", json=body)
    assert response.status_code == 200
    settings = SettingsAPISchema.model_validate(response.json())
    assert len(settings.llm.deployments) == 1  # дубля нет


def test_setup_state_ignores_cloud_deployment_without_key(client):
    """Пресет GigaChat пишется с пустым ключом (см. connectCloud на
    фронтенде) — им нельзя пользоваться, пока ключ не вставлен в
    настройках, поэтому мастер не должен считать шаг пройденным."""
    client.post(
        "/api/v1/setup/deployment",
        json=LLMDeployment(model="gigachat/GigaChat-2").model_dump(),
    )
    state = client.get("/api/v1/setup/state").json()
    assert state["has_deployment"] is False


def test_setup_state_reports_cloud_deployment_with_key(client):
    client.post(
        "/api/v1/setup/deployment",
        json=LLMDeployment(model="gigachat/GigaChat-2", api_key="secret").model_dump(),
    )
    state = client.get("/api/v1/setup/state").json()
    assert state["has_deployment"] is True


def test_setup_local_reports_installed_models(client):
    response = client.get("/api/v1/setup/local")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ollama_state"] == "ready"
    assert payload["installed_models"] == ["qwen2.5:7b", "llama3:8b"]
    assert payload["recommended_tag"] == "qwen2.5:7b"
    assert payload["recommended_installed"] is True


def test_setup_deployment_appends_a_different_model(client):
    client.post(
        "/api/v1/setup/deployment",
        json=LLMDeployment(model="ollama_chat/qwen2.5:7b").model_dump(),
    )
    response: Response = client.post(
        "/api/v1/setup/deployment",
        json=LLMDeployment(model="gigachat/GigaChat-2", api_key="k").model_dump(),
    )
    settings = SettingsAPISchema.model_validate(response.json())
    assert len(settings.llm.deployments) == 2


def test_setup_cloud_models_lists_direct_providers(client):
    response = client.get("/api/v1/setup/cloud-models")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list) and len(payload) > 50
    first = payload[0]
    assert {"model", "label", "provider", "key_url"} <= first.keys()
    assert all(item["key_url"] for item in payload)
