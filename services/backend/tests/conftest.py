from fastapi.testclient import TestClient
from headhunter_backend.log import configure_logging
from headhunter_backend.api.app import app
from headhunter_backend.api.dependencies import get_broadcaster, get_browser
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import AuthStatus
import pytest

configure_logging()


class FakeBrowser:
    def __init__(self):
        self._authenticated = AuthStatus.unauthorized()

    async def get_auth_status(self) -> AuthStatus:
        return self._authenticated

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        self._authenticated = AuthStatus.authorized()


@pytest.fixture
def fake_broadcaster() -> EventBroadcaster:
    return EventBroadcaster()


@pytest.fixture
def fake_browser() -> FakeBrowser:
    return FakeBrowser()


@pytest.fixture
def client(fake_browser: FakeBrowser, fake_broadcaster: EventBroadcaster) -> TestClient:
    app.dependency_overrides[get_browser] = lambda: fake_browser
    app.dependency_overrides[get_broadcaster] = lambda: fake_broadcaster
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
