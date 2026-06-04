from headhunter_backend.api.schemas import SettingsAPISchema
from headhunter_backend.ai.deployment import LLMDeployment
from fastapi import Response


def test_settings_get(client):
    response: Response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    SettingsAPISchema.model_validate(payload)


def test_settings_update(client):
    response: Response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    settings = SettingsAPISchema.model_validate(payload)
    settings.llm.letter_style = "casual"
    response: Response = client.put("/api/v1/settings", json=settings.model_dump())
    assert response.status_code == 200
    payload = response.json()
    updated_settings = SettingsAPISchema.model_validate(payload)
    assert updated_settings.llm.letter_style == "casual"


def test_settings_update_with_ai_rebuild(client):
    response: Response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    settings = SettingsAPISchema.model_validate(payload)
    settings.llm.deployments = [
        LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")
    ]
    response: Response = client.put("/api/v1/settings", json=settings.model_dump())
    assert response.status_code == 200
    payload = response.json()
    updated_settings = SettingsAPISchema.model_validate(payload)
    assert len(updated_settings.llm.deployments) == 1
    assert updated_settings.llm.deployments[0].model == "groq/llama-3.3-70b-versatile"

    settings.llm.deployments = [
        LLMDeployment(model="azure/chatgpt-v-2", api_key="test-key")
    ]
    response: Response = client.put("/api/v1/settings", json=settings.model_dump())
    assert response.status_code == 200
    payload = response.json()
    updated_settings = SettingsAPISchema.model_validate(payload)
    assert len(updated_settings.llm.deployments) == 1
    assert updated_settings.llm.deployments[0].model == "azure/chatgpt-v-2"
