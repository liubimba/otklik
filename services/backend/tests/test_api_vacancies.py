from fastapi import Response
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.models import CoverLetterORM, ApplicationORM
from headhunter_backend.api.schemas import (
    SearchResponseAPISchema,
    ApplicationStatusResponseAPISchema,
    CoverLetterRequest,
    SearchRequestAPISchema,
)
from headhunter_backend.domain.enums import ProcessingState
from headhunter_backend.db.crud import (
    get_latest_cover_letter,
    get_application_by_vacancy_id,
)
from pydantic import HttpUrl


def test_vacancies_get(client):
    response: Response = client.get("/api/v1/vacancies")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    for item in payload:
        VacancyModel.model_validate(item)


def test_vacancies_get_by_id(client):
    response: Response = client.get("/api/v1/vacancies/1")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    VacancyModel.model_validate(payload)


def test_vacancies_get_by_id_not_found(client):
    response: Response = client.get("/api/v1/vacancies/999")
    assert response.status_code == 404


def test_vacancies_search(client):
    response: Response = client.post(
        "/api/v1/vacancies/search",
        json=SearchRequestAPISchema(url=HttpUrl("http://hh.ru")).model_dump(
            mode="json"
        ),
    )
    assert response.status_code == 200
    payload = response.json()
    search_response: SearchResponseAPISchema = SearchResponseAPISchema.model_validate(
        payload
    )
    response = client.get(f"/api/v1/vacancies/search/{search_response.search_id}")
    assert response.status_code == 200
    payload = response.json()
    SearchResponseAPISchema.model_validate(payload)


def test_vacancies_submit(client):
    response: Response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 409
    response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    response = client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequest(text="Test").model_dump(),
    )
    assert response.status_code == 200
    response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 200
    payload = response.json()
    ApplicationStatusResponseAPISchema.model_validate(payload)
    response: Response = client.post("/api/v1/vacancies/999/submit")
    assert response.status_code == 404


async def test_vacancies_queue_for_letter(client):
    response: Response = client.post("/api/v1/vacancies/1/queue_for_letter")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationStatusResponseAPISchema = (
        ApplicationStatusResponseAPISchema.model_validate(payload)
    )
    assert status.vacancy_id == 1
    assert status.status == ProcessingState.LETTER_PENDING

    assert client.post("/api/v1/vacancies/1/queue_for_letter").status_code == 409
    assert client.post("/api/v1/vacancies/999/queue_for_letter").status_code == 404


async def test_vacancies_cover_letter(client, session_factory):
    request: CoverLetterRequest = CoverLetterRequest(text="Test")
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
    status: ApplicationStatusResponseAPISchema = (
        ApplicationStatusResponseAPISchema.model_validate(payload)
    )
    assert status.vacancy_id == 1
    assert status.status == ProcessingState.LETTER_READY

    async with session_factory() as session:
        application: ApplicationORM | None = await get_application_by_vacancy_id(
            session=session, vacancy_id=status.vacancy_id
        )
        assert application is not None
        letter: CoverLetterORM | None = await get_latest_cover_letter(
            session=session, application_id=application.id
        )
        assert letter is not None
        assert letter.text == request.text
        assert letter.application_id == application.id


async def test_vacancies_status(client):
    client.post("/api/v1/vacancies/1/queue_for_letter")
    response: Response = client.get("/api/v1/vacancies/1/status")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationStatusResponseAPISchema = (
        ApplicationStatusResponseAPISchema.model_validate(payload)
    )
    assert status.status == ProcessingState.LETTER_PENDING
    client.post(
        "/api/v1/vacancies/1/cover_letter",
        json=CoverLetterRequest(text="test").model_dump(),
    )
    response = client.get("/api/v1/vacancies/1/status")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationStatusResponseAPISchema = (
        ApplicationStatusResponseAPISchema.model_validate(payload)
    )
    assert status.status == ProcessingState.LETTER_READY
    response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 200
    payload = response.json()
    status: ApplicationStatusResponseAPISchema = (
        ApplicationStatusResponseAPISchema.model_validate(payload)
    )
    assert status.status == ProcessingState.LETTER_SENDING
