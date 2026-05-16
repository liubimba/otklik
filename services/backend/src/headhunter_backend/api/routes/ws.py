from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from headhunter_backend.api.dependencies import BroadcasterDep
from headhunter_backend.log import get_logger
from headhunter_backend.api.events import VacancyEvent
from headhunter_backend.api.mock import mock_vacancy

ws_router: APIRouter = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger(__name__)


@ws_router.websocket("/vacancies")
@ws_router.websocket("/vacancies")
async def websocket_vacancies(websocket: WebSocket) -> None:
    await websocket.accept()
    event: VacancyEvent = VacancyEvent(data=mock_vacancy)
    await websocket.send_text(event.model_dump_json())
    await websocket.close()


@ws_router.websocket("/events")
@ws_router.websocket("/events")
async def websocket_events(websocket: WebSocket, broadcaster: BroadcasterDep) -> None:
    await websocket.accept()
    logger.info("WebSocket connection established on /ws/events")
    broadcaster.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected. Reason: {e.reason}")
    finally:
        broadcaster.unregister(websocket)
    logger.info("WebSocket connection closed on /ws/events")
