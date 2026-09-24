from otklik_backend.api.schemas import ProcessingStatusAPISchema


def test_processing_status_starts_running_and_idle(client):
    response = client.get("/api/v1/processing/status")
    assert response.status_code == 200
    status = ProcessingStatusAPISchema.model_validate(response.json())
    assert status.paused is False
    assert status.in_flight == 0


def test_processing_pause_and_resume_toggle_the_flag(client):
    assert client.post("/api/v1/processing/pause").status_code == 200
    paused = ProcessingStatusAPISchema.model_validate(
        client.get("/api/v1/processing/status").json()
    )
    assert paused.paused is True

    assert client.post("/api/v1/processing/resume").status_code == 200
    resumed = ProcessingStatusAPISchema.model_validate(
        client.get("/api/v1/processing/status").json()
    )
    assert resumed.paused is False


def test_processing_cancel_resumes_and_reports_status(client):
    client.post("/api/v1/processing/pause")
    response = client.post("/api/v1/processing/cancel")
    assert response.status_code == 200
    status = ProcessingStatusAPISchema.model_validate(response.json())
    assert status.paused is False
    assert status.in_flight == 0
