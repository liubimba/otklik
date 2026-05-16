from fastapi import Response
from headhunter_backend.api.routes.vacancies import Vacancy
import headhunter_backend.api.mock as mock
from headhunter_backend.api.schemas import ResponseStatus, SearchResponse


def test_vacancies_get(client):
    response: Response = client.get("/api/v1/vacancies")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    for item in payload:
        Vacancy.model_validate(item)


def test_vacancies_get_by_id(client):
    response: Response = client.get("/api/v1/vacancies/1")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    Vacancy.model_validate(payload)


def test_vacancies_get_by_id_not_found(client):
    response: Response = client.get("/api/v1/vacancies/999")
    assert response.status_code == 404


def test_vacancies_search(client):
    response: Response = client.post(
        "/api/v1/vacancies/search", json=mock.search_filter.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    SearchResponse.model_validate(payload)


def test_vacancies_write(client):
    response: Response = client.post(
        "/api/v1/vacancies/1/write", json=mock.write_request.model_dump()
    )
    assert response.status_code == 200
    payload = response.json()
    ResponseStatus.model_validate(payload)
    response: Response = client.post(
        "/api/v1/vacancies/999/write", json=mock.write_request.model_dump()
    )
    assert response.status_code == 404


def test_vacancies_submit(client):
    response: Response = client.post("/api/v1/vacancies/1/submit")
    assert response.status_code == 200
    payload = response.json()
    ResponseStatus.model_validate(payload)
    response: Response = client.post("/api/v1/vacancies/999/submit")
    assert response.status_code == 404
