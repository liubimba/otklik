from headhunter_backend.api.events import VacancyWSEvent
from headhunter_backend.api.schemas import VacancyAPISchema


def test_api_ws_vacancies(client):
    with client.websocket_connect("/ws/vacancies") as websocket:
        data = websocket.receive_json()
        VacancyWSEvent.model_validate(data)
        assert data.get("type") == "vacancy_new"
        VacancyAPISchema.model_validate(data.get("data"))
