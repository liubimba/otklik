from fastapi import APIRouter, WebSocket
from headhunter_backend.log import get_logger
from headhunter_backend.api.events import VacancyEvent
from headhunter_backend.api.mock import mock_vacancy

ws_router: APIRouter = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger(__name__)


@ws_router.websocket("/vacancies")
async def websocket_vacancies(websocket: WebSocket) -> None:
    await websocket.accept()
    event: VacancyEvent = VacancyEvent(data=mock_vacancy)
    await websocket.send_text(event.model_dump_json())
    await websocket.close()


@ws_router.websocket("/events")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close()
