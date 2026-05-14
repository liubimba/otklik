from fastapi.testclient import TestClient
from headhunter_backend.log import configure_logging
import pytest

configure_logging()


@pytest.fixture
def client() -> TestClient:
    from headhunter_backend.api.app import app

    return TestClient(app)
