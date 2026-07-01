from fastapi import Response
from headhunter_backend.db.models import CoverLetterORM, ApplicationORM
from headhunter_backend.api.schemas import (
    ApplicationAPISchema,
    CoverLetterRequestAPISchema,
    CoverLetterAPISchema,
    ProcessingState,
    VacanciesStartSearchRequestAPISchema,
    VacanciesSearchAPISchema,
    VacancyAPISchema,
)
from pydantic import HttpUrl
from headhunter_backend.db.repositories.applications import ApplicationRepository
from headhunter_backend.db.repositories.cover_letters import CoverLetterRepository


def test_vacancies_get(client):
    response: Response = client.get("/api/v1/vacancies")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    for item in payload:
        VacancyAPISchema.model_validate(item)


def test_vacancies_get_by_id(client):
    response: Response = client.get("/api/v1/vacancies/1")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    VacancyAPISchema.model_validate(payload)


def test_vacancies_get_by_id_not_found(client):
    response: Response = client.get("/api/v1/vacancies/999")
    assert response.status_code == 404


def test_vacancies_search(client):
    response: Response = client.post(
        "/api/v1/vacancies/search",
        json=VacanciesStartSearchRequestAPISchema(
            url=HttpUrl("http://hh.ru")
        ).model_dump(mode="json"),
    )
    assert response.status_code == 200
    payload = response.json()
    search_response: VacanciesSearchAPISchema = VacanciesSearchAPISchema.model_validate(
        payload
    )
    response = client.get(f"/api/v1/vacancies/search/{search_response.search_id}")
    assert response.status_code == 200
    payload = response.json()
    VacanciesSearchAPISchema.model_validate(payload)


def test_vacancies_submit(client):
    response: Response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 409
    response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    response = client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="Test").model_dump(),
    )
    assert response.status_code == 200
    response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 200
    payload = response.json()
    ApplicationAPISchema.model_validate(payload)
    response: Response = client.post("/api/v1/vacancies/999/submit")
    assert response.status_code == 404


async def test_vacancies_queue_for_letter(client):
    response: Response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationAPISchema = ApplicationAPISchema.model_validate(payload)
    assert status.vacancy_id == 1
    assert status.status == ProcessingState.LETTER_PENDING

    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 409
    assert client.post("/api/v1/vacancies/999/queue_for_letter").status_code == 404


async def test_vacancies_cover_letter(client, session_factory):
    request: CoverLetterRequestAPISchema = CoverLetterRequestAPISchema(text="Test")
    response: Response = client.post(
        "/api/v1/vacancies/1/cover_letter", json=request.model_dump()
    )
    assert response.status_code == 409
    response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    response = client.post(
        "/api/v1/vacancies/1/cover_letter", json=request.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    cover_letter: CoverLetterAPISchema = CoverLetterAPISchema.model_validate(payload)
    assert cover_letter.text == request.text
    assert cover_letter.version == 1
    assert cover_letter.created_at is not None

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(session=session, vacancy_id=1)
        assert application is not None
        letter: (
            CoverLetterORM | None
        ) = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=application.id
        )
        assert letter is not None
        assert letter.text == request.text
        assert letter.application_id == application.id


async def test_vacancies_double_cover_letter(client, session_factory):
    text: str = "Test"
    request: CoverLetterRequestAPISchema = CoverLetterRequestAPISchema(text=text)
    response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    response = client.post(
        "/api/v1/vacancies/1/cover_letter", json=request.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    cover_letter: CoverLetterAPISchema = CoverLetterAPISchema.model_validate(payload)
    assert cover_letter.version == 1
    assert cover_letter.text == text
    response = client.post(
        "/api/v1/vacancies/1/cover_letter", json=request.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    cover_letter: CoverLetterAPISchema = CoverLetterAPISchema.model_validate(payload)
    assert cover_letter.version == 2
    assert cover_letter.text == text
    response = client.post("/api/v1/vacancies/1/review")
    assert response.status_code == 200
    response = client.post(
        "/api/v1/vacancies/1/cover_letter", json=request.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    cover_letter: CoverLetterAPISchema = CoverLetterAPISchema.model_validate(payload)
    assert cover_letter.version == 3
    assert cover_letter.text == text

    async with session_factory() as session:
        application: (
            ApplicationORM | None
        ) = await ApplicationRepository.get_by_vacancy_id(session=session, vacancy_id=1)
        assert application is not None
        letter: (
            CoverLetterORM | None
        ) = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=application.id
        )
        assert letter is not None
        assert letter.text == request.text
        assert letter.application_id == application.id


def test_get_cover_letter_404_no_application(client):
    assert client.get("/api/v1/vacancies/1/cover_letter").status_code == 404


def test_get_cover_letter_404_letter_pending(client):
    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 200
    assert client.get("/api/v1/vacancies/1/cover_letter").status_code == 404


def test_get_cover_letter_happy(client):
    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 200
    assert (
        client.post(
            "/api/v1/vacancies/1/cover_letter",
            json=CoverLetterRequestAPISchema(text="hello").model_dump(),
        ).status_code
        == 200
    )
    response = client.get("/api/v1/vacancies/1/cover_letter")
    assert response.status_code == 200
    letter = CoverLetterAPISchema.model_validate(response.json())
    assert letter.text == "hello"
    assert letter.version == 1


def test_post_cover_letter_409_no_application(client):
    response = client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    assert response.status_code == 409


def test_post_cover_letter_404_no_vacancy(client):
    response = client.post(
        "/api/v1/vacancies/999/cover_letter",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    assert response.status_code == 404


def test_review_happy(client):
    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 200
    assert (
        client.post(
            "/api/v1/vacancies/1/cover_letter",
            json=CoverLetterRequestAPISchema(text="x").model_dump(),
        ).status_code
        == 200
    )
    response = client.post("/api/v1/vacancies/1/review")
    assert response.status_code == 200
    payload = ApplicationAPISchema.model_validate(response.json())
    assert payload.status == ProcessingState.LETTER_REVIEWING


def test_review_409_letter_pending(client):
    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 200
    assert client.post("/api/v1/vacancies/1/review").status_code == 409


def test_review_404_no_vacancy(client):
    assert client.post("/api/v1/vacancies/999/review").status_code == 404


def test_review_409_no_application(client):
    assert client.post("/api/v1/vacancies/1/review").status_code == 409


def test_skip_happy(client):
    client.post("/api/v1/vacancies/1/queue_for_letter")
    client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    client.post("/api/v1/vacancies/1/review")
    response = client.post("/api/v1/vacancies/1/skip")
    assert response.status_code == 200
    payload = ApplicationAPISchema.model_validate(response.json())
    assert payload.status == ProcessingState.SKIPPED


def test_skip_409_letter_ready(client):
    client.post("/api/v1/vacancies/1/queue_for_letter")
    client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    # skip allowed only from LETTER_REVIEWING per state machine
    assert client.post("/api/v1/vacancies/1/skip").status_code == 409


def test_skip_404_no_vacancy(client):
    assert client.post("/api/v1/vacancies/999/skip").status_code == 404


def test_skip_409_no_application(client):
    assert client.post("/api/v1/vacancies/1/skip").status_code == 409


def test_application_ws_event_published_on_transitions(client, recording_broadcaster):
    from headhunter_backend.api.events import ApplicationWSEvent

    def app_events() -> list[ApplicationWSEvent]:
        return [
            e for e in recording_broadcaster.events if isinstance(e, ApplicationWSEvent)
        ]

    client.post("/api/v1/vacancies/1/queue_for_letter")
    client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="x").model_dump(),
    )
    client.post("/api/v1/vacancies/1/review")
    client.post("/api/v1/vacancies/1/skip")

    statuses = [e.data.status for e in app_events()]
    assert statuses == [
        ProcessingState.LETTER_PENDING,
        ProcessingState.LETTER_READY,
        ProcessingState.LETTER_REVIEWING,
        ProcessingState.SKIPPED,
    ]
    for e in app_events():
        assert e.data.vacancy_id == 1


async def test_vacancies_status(client):
    client.post("/api/v1/vacancies/1/queue_for_letter")
    response: Response = client.get("/api/v1/vacancies/1/status")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationAPISchema = ApplicationAPISchema.model_validate(payload)
    assert status.status == ProcessingState.LETTER_PENDING
    client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequestAPISchema(text="test").model_dump(),
    )
    response = client.get("/api/v1/vacancies/1/status")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationAPISchema = ApplicationAPISchema.model_validate(payload)
    assert status.status == ProcessingState.LETTER_READY
    response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationAPISchema = ApplicationAPISchema.model_validate(payload)
    assert status.status == ProcessingState.LETTER_SENDING
