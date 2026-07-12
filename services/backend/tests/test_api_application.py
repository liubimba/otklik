from fastapi import Response

from otklik_backend.api.schemas import (
    ApplicationDetailAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
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

    # State did not change (still LETTER_READY, not LETTER_GENERATED).
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
    """Regression: the UI keeps the textarea editable in ERROR state so the
    user can polish the draft after a failed submit / LLM error. The save
    endpoint must accept the write without a status guard — it does not
    touch the state machine, only appends a new CoverLetter version."""
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    # Sanity: we are actually in ERROR.
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

    # Status stays ERROR — save does NOT move the state machine.
    after = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert after.status == ProcessingState.ERROR
    assert after.latest_letter is not None
    assert after.latest_letter.text == "Repaired draft"


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
    """The UI collapses the error-state Retry button into Submit — a failed
    submit should be re-attempted without a forced LLM regeneration. This
    exercises the ERROR → LETTER_SENDING arc added to the state machine,
    plus the atomic dirty-submit path (text saved before the transition)."""
    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        await ApplicationRepository.transition(
            session=session,
            application_id=app_id,
            to_state=ApplicationEvent.FAIL,
        )

    # Sanity: we're actually in ERROR.
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
    """Regression 2026-07-02: POST /application/generate used to block on
    the LLM synchronously (2-3s) and return with status=letter_ready.
    Because the intermediate LETTER_PENDING transient was too short to
    catch a WS refetch, the UI never saw it and no spinner was rendered
    during regeneration — the user reported the sheet stayed on the
    "letter ready" view even while the LLM was running.

    Fix: the endpoint only fires the state-machine transition to
    LETTER_PENDING, then returns the ApplicationDetail immediately.
    LetterPendingWorker picks up the resulting ApplicationWSEvent and
    runs the LLM in the background. From the client's point of view,
    the status is LETTER_PENDING durably for the entire generation
    span, and the spinner is visible until letter_ready arrives.
    """
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

    # Response body must be an ApplicationDetail-shaped payload, not the
    # AICoverLetterResult it used to return.
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == ProcessingState.LETTER_PENDING.value, body

    # AI Layer must NOT have been driven from the handler — the worker
    # owns that call now. Guards against a partial refactor that flips
    # the response type but keeps the sync LLM call.
    assert ai_layer_with_router._router.acompletion.await_count == 0


async def test_generate_returns_409_when_application_is_terminal(
    client, session_factory, ai_layer_with_router
):
    """Regression: /generate crashed with 500 on any TransitionNotAllowed.
    Wrap the call so terminal / in-flight states (LETTER_SENT here) get
    409 instead of a stack trace."""
    from tests.test_ai import _fake_model_response

    ai_layer_with_router._router.acompletion.return_value = _fake_model_response(
        content="unused"
    )

    app_id = await _seed_letter_ready(session_factory)
    async with session_factory() as session:
        # Walk the state machine into LETTER_SENT (terminal-ish).
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
    """Same transition, but the client did not send `text` — the existing
    latest letter is used verbatim. Confirms the endpoint doesn't require
    a body override to move ERROR → LETTER_SENDING."""
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
    """Regression: after a first Submit that landed in NOT_AUTHORIZED and
    paused the LetterSendingWorker, the API used to happily accept a second
    Submit — the state machine still allowed ERROR → LETTER_SENDING and
    the endpoint did not know about the worker's pause state. Result: the
    application sat in LETTER_SENDING forever (the worker was still
    blocked on `_resume_event.wait()` because no AuthWSEvent(authorized)
    had arrived yet), which the UI reads as an infinite "Откликаемся…"
    spinner (reported by user 2026-07-02).

    The fix must propagate the worker pause state to the client via 409
    so the UI can surface a re-auth prompt instead of hanging.
    """
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

    # Sanity: preconditions of the bug scenario.
    detail_before = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail_before.status == ProcessingState.ERROR
    assert fake_orchestrator.is_paused()

    response: Response = client.post(
        "/api/v1/vacancies/1/application/submit",
        json=SubmitApplicationRequestAPISchema().model_dump(),
    )

    # After fix: request is refused with 409, application stays in ERROR
    # and the response body carries the pause reason so the UI can react.
    assert response.status_code == 409, response.text
    assert "authorized" in response.json()["detail"].lower()

    detail_after = ApplicationDetailAPISchema.model_validate(
        client.get("/api/v1/vacancies/1/application").json()
    )
    assert detail_after.status == ProcessingState.ERROR


async def test_skip_transitions(client, session_factory):
    await _seed_letter_ready(session_factory)
    # LETTER_READY → LETTER_REVIEWING → SKIPPED per state machine
    # But new endpoint tries direct SKIP; let's move to reviewing first.
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
