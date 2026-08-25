def test_cors_allows_the_electron_app_origin(client):
    response = client.get("/api/v1/system/health", headers={"origin": "app://bundle"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "app://bundle"
