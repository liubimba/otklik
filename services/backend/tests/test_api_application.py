from fastapi import Response

from otklik_backend.api.schemas import (
    ApplicationDetailAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
    ErrorDomain,
    ProcessingState,
    SubmitApplicationRequestAPISchema,
)
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent


async def _seed_letter_ready(session_factory, vacancy_id: int = 1) -> int:
    async with session_factory() as session:
        app = await ApplicationRepository.create(session=session, vacancy_id=vacancy_id)
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.LETTER_GENERATED,
        )
        await CoverLetterRepository.create(
            session=session, application_id=app.id, text="Seed letter"
        )
        return app.id


async def test_get_application_returns_combined_state(client, session_factory):
    await _seed_letter_ready(session_factory)

    response: Response = client.get("/api/v1/vacancies/1/application")
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.LETTER_READY
    assert detail.latest_letter is not None
    assert detail.latest_letter.text == "Seed letter"
    assert detail.letters_count == 1


async def test_get_application_404_when_no_application(client):
    response: Response = client.get("/api/v1/vacancies/1/application")
    assert response.status_code == 404


async def test_get_letters_history(client, session_factory):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await CoverLetterRepository.create(
            session=session, application_id=app_id, text="Second version"
        )

    response: Response = client.get("/api/v1/vacancies/1/application/letters")
    assert response.status_code == 200
    letters = [CoverLetterAPISchema.model_validate(item) for item in response.json()]
    assert len(letters) == 2


async def test_save_creates_new_version_without_transition(client, session_factory):
    await _seed_letter_ready(session_factory)

    response: Response = client.post(
        "/api/v1/vacancies/1/application/save",
        json=CoverLetterRequestAPISchema(text="Edited draft").model_dump(),
    )
    assert response.status_code == 200
    letter = CoverLetterAPISchema.model_validate(response.json())
    assert letter.text == "Edited draft"
    assert letter.version == 2

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.LETTER_READY


async def test_save_409_no_application(client):
    response: Response = client.post(
        "/api/v1/vacancies/1/application/save",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    assert response.status_code == 409


async def test_save_works_in_error_state(client, session_factory):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.ERROR

    response: Response = client.post(
        "/api/v1/vacancies/1/application/save",
        json=CoverLetterRequestAPISchema(text="Repaired draft").model_dump(),
    )
    assert response.status_code == 200
    letter = CoverLetterAPISchema.model_validate(response.json())
    assert letter.text == "Repaired draft"
    assert letter.version == 2

    after = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert after.status == ProcessingState.ERROR
    assert after.latest_letter is not None
    assert after.latest_letter.text == "Repaired draft"


async def test_fail_transition_tags_error_domain_as_model(client, session_factory):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
            error_message="connection refused",
        )

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.ERROR
    assert detail.reason == "connection refused"
    assert detail.error_domain == ErrorDomain.MODEL


async def test_submission_failed_transition_tags_error_domain_as_submission(
    client, session_factory
):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.SUBMIT,
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.SUBMISSION_FAILED,
            error_message="verification timeout",
        )

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.ERROR
    assert detail.reason == "verification timeout"
    assert detail.error_domain == ErrorDomain.SUBMISSION


async def test_error_domain_clears_when_recovering_out_of_error(
    client, session_factory
):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
            error_message="connection refused",
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.LETTER_GENERATED,
        )

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.LETTER_READY
    assert detail.error_domain is None


async def test_submit_transitions_and_atomically_saves_text(client, session_factory):
    await _seed_letter_ready(session_factory)

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema(text="Final draft").model_dump(),
    )
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.LETTER_SENDING
    assert detail.latest_letter is not None
    assert detail.latest_letter.text == "Final draft"


async def test_submit_without_text_uses_existing_letter(client, session_factory):
    await _seed_letter_ready(session_factory)

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema().model_dump(),
    )
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.LETTER_SENDING
    assert detail.latest_letter is not None
    assert detail.latest_letter.text == "Seed letter"


async def test_submit_404_when_vacancy_missing(client):
    response: Response = client.post(
        "/api/v1/vacancies/999/application/submit",
        json=SubmitApplicationRequestAPISchema().model_dump(),
    )
    assert response.status_code == 404


async def test_submit_from_error_state_transitions_and_saves_text(
    client, session_factory
):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    detail = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail.status == ProcessingState.ERROR

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema(
            text="Edited after failure"
        ).model_dump(),
    )
    assert response.status_code == 200
    result = ApplicationDetailAPISchema.model_validate(response.json())
    assert result.status == ProcessingState.LETTER_SENDING
    assert result.latest_letter is not None
    assert result.latest_letter.text == "Edited after failure"


async def test_generate_returns_immediately_with_letter_pending_status(
    client, session_factory, ai_layer_with_router
):
    from tests.test_ai import _fake_model_response

    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="Fresh letter"
    )

    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    response: Response = client.post("/api/v1/vacancies/1/application/generate")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == ProcessingState.LETTER_PENDING.value, body

    assert ai_layer_with_router._router.acompletion.await_count == 0


async def test_generate_returns_409_when_application_is_terminal(
    client, session_factory, ai_layer_with_router
):
    from tests.test_ai import _fake_model_response

    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="unused"
    )

    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session, application_id=app_id, to_state=ApplicationEvent.SUBMIT
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.SUBMISSION_OK,
        )

    response: Response = client.post("/api/v1/vacancies/1/application/generate")
    assert response.status_code == 409
    assert "Cannot regenerate letter" in response.json()["detail"]


async def test_submit_from_error_without_text_reuses_existing_letter(
    client, session_factory
):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema().model_dump(),
    )
    assert response.status_code == 200
    result = ApplicationDetailAPISchema.model_validate(response.json())
    assert result.status == ProcessingState.LETTER_SENDING
    assert result.latest_letter is not None
    assert result.latest_letter.text == "Seed letter"


async def test_submit_returns_409_when_worker_is_paused_for_auth(
    client, session_factory, fake_orchestrator
):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )
    fake_orchestrator.pause(
        reason=fake_orchestrator.PAUSE_REASON_NOT_AUTHORIZED,
    )

    detail_before = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail_before.status == ProcessingState.ERROR
    assert fake_orchestrator.is_paused()

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema().model_dump(),
    )

    assert response.status_code == 409, response.text
    assert "authorized" in response.json()["detail"].lower()

    detail_after = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail_after.status == ProcessingState.ERROR


async def test_skip_from_error_returns_200_not_409(client, session_factory):
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    response: Response = client.post("/api/v1/vacancies/1/application/skip")
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.SKIPPED


async def test_skip_from_letter_ready_without_opening_the_sheet(
    client, session_factory
):
    await _seed_letter_ready(session_factory)

    response: Response = client.post("/api/v1/vacancies/1/application/skip")
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.SKIPPED


async def test_skip_transitions(client, session_factory):
    await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        app = await ApplicationRepository.get_by_vacancy_id(
            session=session, vacancy_id=1
        )
        await ApplicationRepository.transition(
            session=session,
            application_id=app.id,
            to_state=ApplicationEvent.SEND_FOR_REVIEW,
        )

    response: Response = client.post("/api/v1/vacancies/1/application/skip")
    assert response.status_code == 200
    detail = ApplicationDetailAPISchema.model_validate(response.json())
    assert detail.status == ProcessingState.SKIPPED
