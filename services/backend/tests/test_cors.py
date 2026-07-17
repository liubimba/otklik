from fastapi import Response
from fastapi.testclient import TestClient


def test_cors_allows_the_app_origin(client: TestClient) -> None:
    response: Response = client.get(
        "/api/v1/settings", headers={"Origin": "http://localhost:1420"}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:1420"


def test_cors_rejects_a_foreign_origin(client: TestClient) -> None:
    response: Response = client.get(
        "/api/v1/settings", headers={"Origin": "https://evil.example"}
    )
    assert "access-control-allow-origin" not in response.headers
    assert response.headers.get("access-control-allow-origin") != "*"


def test_cors_preflight_from_a_foreign_origin_is_not_allowed(
    client: TestClient,
) -> None:
    response: Response = client.options(
        "/api/v1/settings",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "PUT",
        },
    )
    assert "access-control-allow-origin" not in response.headers
