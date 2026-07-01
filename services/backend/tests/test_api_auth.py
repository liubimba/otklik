from fastapi import Response
from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.core.events import AuthWSEvent


def test_api_auth_status(client, fake_browser):
    fake_browser._authenticated = AuthStatusAPISchema.unauthorized()
    response: Response = client.get("/api/v1/auth/status")
    assert response.status_code == 200
    payload = response.json()
    status: AuthStatusAPISchema = AuthStatusAPISchema.model_validate(payload)
    assert not status.is_authorized()

    fake_browser._authenticated = AuthStatusAPISchema.authorized()
    response: Response = client.get("/api/v1/auth/status")
    assert response.status_code == 200
    payload = response.json()
    status: AuthStatusAPISchema = AuthStatusAPISchema.model_validate(payload)
    assert status.is_authorized()


def test_api_auth(client, fake_browser):
    with client.websocket_connect("/ws/events") as ws:
        fake_browser._authenticated = AuthStatusAPISchema.unauthorized()
        response: Response = client.post("/api/v1/auth/sign-in")
        assert response.status_code == 200
        payload = response.json()
        status: AuthStatusAPISchema = AuthStatusAPISchema.model_validate(payload)
        assert status.status == "authorizing"
        payload = ws.receive_json()
        auth_event: AuthWSEvent = AuthWSEvent.model_validate(payload)
        assert auth_event.data.is_authorized()
