from headhunter_backend.api.schemas import Settings
from fastapi import Response


def test_settings_get(client):
    response: Response = client.get("/api/v1/settings/")
    assert response.status_code == 200
    payload = response.json()
    Settings.model_validate(payload)


def test_settings_update(client):
    response: Response = client.get("/api/v1/settings/")
    assert response.status_code == 200
    payload = response.json()
    settings = Settings.model_validate(payload)
    settings.letter_style = "casual"
    response: Response = client.put("/api/v1/settings/", json=settings.model_dump())
    assert response.status_code == 200
    payload = response.json()
    updated_settings = Settings.model_validate(payload)
    assert updated_settings.letter_style == "casual"
