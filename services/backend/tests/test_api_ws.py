from headhunter_backend.api.schemas import Vacancy
from headhunter_backend.api.events import VacancyEvent


def test_api_ws_vacancies(client):
    with client.websocket_connect("/ws/vacancies") as websocket:
        data = websocket.receive_json()
        VacancyEvent.model_validate(data)
        assert data.get("type") == "vacancy_new"
        Vacancy.model_validate(data.get("data"))
