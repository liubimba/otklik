from headhunter_backend.api.events import VacancyEvent
from headhunter_backend.domain.models import VacancyModel


def test_api_ws_vacancies(client):
    with client.websocket_connect("/ws/vacancies") as websocket:
        data = websocket.receive_json()
        VacancyEvent.model_validate(data)
        assert data.get("type") == "vacancy_new"
        VacancyModel.model_validate(data.get("data"))
