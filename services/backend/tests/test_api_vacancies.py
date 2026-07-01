from fastapi import Response

from headhunter_backend.api.schemas import VacancyAPISchema


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
