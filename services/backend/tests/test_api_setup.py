from collections.abc import AsyncIterator

from fastapi import Response

from otklik_backend.api.app import app
from otklik_backend.api.dependencies import get_ollama_gate
from otklik_backend.api.schemas import LLMDeploymentWriteAPISchema, SettingsAPISchema
from otklik_backend.secrets.store import account_for
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


def test_setup_trial_generates_a_letter(client):
    response = client.post(
        "/api/v1/setup/trial",
        json={
            "deployment": {"model": "ollama_chat/qwen2.5:7b", "api_base": "http://h"},
            "deadline_sec": 45,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is True
    assert payload["letter"]


def test_setup_trial_does_not_persist_the_key(client, fake_secret_store):
    """Ключ в /trial живёт только на время замера: не должен попасть ни в
    хранилище, ни в строку настроек."""
    response = client.post(
        "/api/v1/setup/trial",
        json={
            "deployment": {"model": "gigachat/GigaChat-2", "api_key": "sk-trial"},
            "deadline_sec": 45,
        },
    )
    assert response.status_code == 200
    assert fake_secret_store.items == {}

    settings = SettingsAPISchema.model_validate(client.get("/api/v1/settings").json())
    assert settings.llm.deployments == []


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
    body = LLMDeploymentWriteAPISchema(
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
    body = LLMDeploymentWriteAPISchema(
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
        json=LLMDeploymentWriteAPISchema(model="gigachat/GigaChat-2").model_dump(),
    )
    state = client.get("/api/v1/setup/state").json()
    assert state["has_deployment"] is False


def test_setup_state_reports_cloud_deployment_with_key(client):
    client.post(
        "/api/v1/setup/deployment",
        json=LLMDeploymentWriteAPISchema(
            model="gigachat/GigaChat-2", api_key="secret"
        ).model_dump(),
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
        json=LLMDeploymentWriteAPISchema(model="ollama_chat/qwen2.5:7b").model_dump(),
    )
    response: Response = client.post(
        "/api/v1/setup/deployment",
        json=LLMDeploymentWriteAPISchema(
            model="gigachat/GigaChat-2", api_key="k"
        ).model_dump(),
    )
    settings = SettingsAPISchema.model_validate(response.json())
    assert len(settings.llm.deployments) == 2


def test_setup_deployment_makes_the_new_one_primary(client):
    first = client.post(
        "/api/v1/setup/deployment",
        json={"model": "gigachat/GigaChat-2", "api_key": "k1"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/v1/setup/deployment",
        json={"model": "ollama_chat/qwen2.5:7b", "api_base": "http://h"},
    )
    assert second.status_code == 200
    deployments = second.json()["llm"]["deployments"]
    # новый (локальный) — первым, прежний (облачный) — фолбэком
    assert deployments[0]["model"] == "ollama_chat/qwen2.5:7b"
    assert deployments[1]["model"] == "gigachat/GigaChat-2"


def test_setup_deployment_is_idempotent_and_promotes(client):
    payload = {"model": "gigachat/GigaChat-2", "api_key": "k1"}
    client.post("/api/v1/setup/deployment", json=payload)
    client.post(
        "/api/v1/setup/deployment",
        json={"model": "openai/gpt-4o", "api_key": "k2"},
    )
    # повторно шлём первый — он должен всплыть в основные, без дубля
    again = client.post("/api/v1/setup/deployment", json=payload)
    deployments = again.json()["llm"]["deployments"]
    models = [d["model"] for d in deployments]
    assert models == ["gigachat/GigaChat-2", "openai/gpt-4o"]


def test_setup_deployment_rotating_key_replaces_not_duplicates(
    client, fake_secret_store
):
    """Регрессия на удалённый эндшпиль-шорткат: тот же (model, api_base) с
    новым ключом должен заменить запись и её секрет, а не потеряться из-за
    «список не изменился» (эта проверка сравнивала целые модели — а с задачи
    5, когда ключ уйдёт из LLMDeployment, такое сравнение было бы всегда
    равным при ротации, и новый ключ тихо не долетал бы до хранилища)."""
    payload = {"model": "gigachat/GigaChat-2", "api_base": None}
    first = client.post(
        "/api/v1/setup/deployment", json={**payload, "api_key": "sk-old"}
    )
    assert first.status_code == 200
    first_settings = SettingsAPISchema.model_validate(first.json())
    assert len(first_settings.llm.deployments) == 1
    first_id = first_settings.llm.deployments[0].id
    assert fake_secret_store.items[account_for(first_id)] == "sk-old"

    second = client.post(
        "/api/v1/setup/deployment", json={**payload, "api_key": "sk-new"}
    )
    assert second.status_code == 200
    second_settings = SettingsAPISchema.model_validate(second.json())

    assert len(second_settings.llm.deployments) == 1  # не дубль
    second_id = second_settings.llm.deployments[0].id
    assert second_id == first_id  # id переиспользован — не сирота в хранилище
    assert fake_secret_store.items[account_for(second_id)] == "sk-new"


def test_setup_cloud_models_lists_direct_providers(client):
    response = client.get("/api/v1/setup/cloud-models")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list) and len(payload) > 50
    first = payload[0]
    assert {"model", "label", "provider", "key_url"} <= first.keys()
    assert all(item["key_url"] for item in payload)


def test_setup_claude_reports_ready(client):
    response = client.get("/api/v1/setup/claude")
    assert response.status_code == 200
    payload = response.json()
    assert payload["claude_state"] == "ready"
    assert payload["default_model"] == "claude-code/sonnet"
    models = [opt["model"] for opt in payload["model_options"]]
    assert models == ["claude-code/sonnet", "claude-code/opus", "claude-code/haiku"]


def test_setup_state_exposes_claude_available(client):
    state = client.get("/api/v1/setup/state").json()
    assert state["claude_available"] is True


def test_setup_claude_deployment_counts_as_configured(client):
    client.post(
        "/api/v1/setup/deployment",
        json=LLMDeploymentWriteAPISchema(model="claude-code/sonnet").model_dump(),
    )
    state = client.get("/api/v1/setup/state").json()
    assert state["has_deployment"] is True


def test_setup_deployment_response_never_contains_api_key(client):
    import json as _json

    response = client.post(
        "/api/v1/setup/deployment",
        json={"model": "gigachat/GigaChat-2", "api_key": "sk-secret"},
    )
    assert response.status_code == 200
    assert '"api_key"' not in _json.dumps(response.json())
