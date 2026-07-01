from fastapi import Response

from headhunter_backend.api.schemas import (
    ApplicationDetailAPISchema,
    CoverLetterAPISchema,
    CoverLetterRequestAPISchema,
    ProcessingState,
    SubmitApplicationRequestAPISchema,
)
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository
from headhunter_backend.orchestrator.state_machine import ApplicationEvent


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
