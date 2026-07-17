import json

from fastapi import Response

from otklik_backend.api.schemas import SettingsAPISchema
from otklik_backend.secrets.store import account_for


def test_settings_get(client):
    response: Response = client.get("/api/v1/settings")
    assert response.status_code == 200
    payload = response.json()
    SettingsAPISchema.model_validate(payload)


def test_settings_get_never_returns_api_key(client, fake_secret_store):
    settings = SettingsAPISchema.model_validate(client.get("/api/v1/settings").json())
    body = settings.model_dump(mode="json")
    body["llm"]["deployments"] = [
        {"model": "gigachat/GigaChat-2", "api_key": "sk-original"}
    ]
    put_response = client.put("/api/v1/settings", json=body)
    assert put_response.status_code == 200

    response = client.get("/api/v1/settings")
    payload = response.json()

    assert '"api_key"' not in json.dumps(payload)
    assert payload["llm"]["deployments"][0]["has_api_key"] is True


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


def test_settings_update_never_returns_api_key(client):
    body = SettingsAPISchema.model_validate(
        client.get("/api/v1/settings").json()
    ).model_dump(mode="json")
    body["llm"]["deployments"] = [
        {"model": "groq/llama-3.3-70b-versatile", "api_key": "sk-put"}
    ]
    response: Response = client.put("/api/v1/settings", json=body)
    assert response.status_code == 200
    assert '"api_key"' not in json.dumps(response.json())


def test_settings_update_with_ai_rebuild(client):
    body = SettingsAPISchema.model_validate(
        client.get("/api/v1/settings").json()
    ).model_dump(mode="json")
    body["llm"]["deployments"] = [
        {"model": "groq/llama-3.3-70b-versatile", "api_key": "test-key"}
    ]
    response: Response = client.put("/api/v1/settings", json=body)
    assert response.status_code == 200
    payload = response.json()
    updated_settings = SettingsAPISchema.model_validate(payload)
    assert len(updated_settings.llm.deployments) == 1
    assert updated_settings.llm.deployments[0].model == "groq/llama-3.3-70b-versatile"

    body["llm"]["deployments"] = [{"model": "azure/chatgpt-v-2", "api_key": "test-key"}]
    response: Response = client.put("/api/v1/settings", json=body)
    assert response.status_code == 200
    payload = response.json()
    updated_settings = SettingsAPISchema.model_validate(payload)
    assert len(updated_settings.llm.deployments) == 1
    assert updated_settings.llm.deployments[0].model == "azure/chatgpt-v-2"


def test_settings_update_unrelated_field_keeps_api_key(client, fake_secret_store):
    seed = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [
                    {"model": "gigachat/GigaChat-2", "api_key": "sk-original"}
                ]
            }
        },
    )
    assert seed.status_code == 200
    seeded = SettingsAPISchema.model_validate(seed.json())
    deployment_id = seeded.llm.deployments[0].id
    assert fake_secret_store.items[account_for(deployment_id)] == "sk-original"

    get_response = client.get("/api/v1/settings")
    payload = get_response.json()
    payload["search"]["max_pages"] = 7
    assert '"api_key"' not in json.dumps(payload)

    put_response = client.put("/api/v1/settings", json=payload)
    assert put_response.status_code == 200
    updated = SettingsAPISchema.model_validate(put_response.json())

    assert updated.search.max_pages == 7
    assert len(updated.llm.deployments) == 1
    assert updated.llm.deployments[0].id == deployment_id
    assert updated.llm.deployments[0].has_api_key is True
    assert fake_secret_store.items[account_for(deployment_id)] == "sk-original"


def test_settings_update_rotates_key(client, fake_secret_store):
    seed = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [{"model": "gigachat/GigaChat-2", "api_key": "sk-old"}]
            }
        },
    )
    seeded = SettingsAPISchema.model_validate(seed.json())
    deployment_id = seeded.llm.deployments[0].id

    rotate = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [
                    {
                        "id": deployment_id,
                        "model": "gigachat/GigaChat-2",
                        "api_key": "sk-new",
                    }
                ]
            }
        },
    )
    assert rotate.status_code == 200
    updated = SettingsAPISchema.model_validate(rotate.json())
    assert updated.llm.deployments[0].has_api_key is True
    assert fake_secret_store.items[account_for(deployment_id)] == "sk-new"


def test_settings_update_clears_key(client, fake_secret_store):
    seed = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [{"model": "gigachat/GigaChat-2", "api_key": "sk-old"}]
            }
        },
    )
    seeded = SettingsAPISchema.model_validate(seed.json())
    deployment_id = seeded.llm.deployments[0].id

    cleared = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [
                    {"id": deployment_id, "model": "gigachat/GigaChat-2", "api_key": ""}
                ]
            }
        },
    )
    assert cleared.status_code == 200
    updated = SettingsAPISchema.model_validate(cleared.json())
    assert updated.llm.deployments[0].has_api_key is False
    assert account_for(deployment_id) not in fake_secret_store.items


def test_settings_update_drops_deployment_deletes_its_key(client, fake_secret_store):
    seed = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "deployments": [
                    {"model": "gigachat/GigaChat-2", "api_key": "sk-a"},
                    {"model": "openai/gpt-4o", "api_key": "sk-b"},
                ]
            }
        },
    )
    seeded = SettingsAPISchema.model_validate(seed.json())
    kept_id = seeded.llm.deployments[0].id
    dropped_id = seeded.llm.deployments[1].id
    assert fake_secret_store.items[account_for(dropped_id)] == "sk-b"

    dropped = client.put(
        "/api/v1/settings",
        json={
            "llm": {"deployments": [{"id": kept_id, "model": "gigachat/GigaChat-2"}]}
        },
    )
    assert dropped.status_code == 200
    updated = SettingsAPISchema.model_validate(dropped.json())
    assert len(updated.llm.deployments) == 1
    assert updated.llm.deployments[0].has_api_key is True
    assert fake_secret_store.items[account_for(kept_id)] == "sk-a"
    assert account_for(dropped_id) not in fake_secret_store.items
