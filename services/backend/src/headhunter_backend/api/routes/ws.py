from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from headhunter_backend.api.dependencies import BroadcasterDep
from headhunter_backend.log import get_logger
from headhunter_backend.api.events import VacancyEvent
from headhunter_backend.db.crud import list_vacancies
from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.db.converters import vacancy_to_model
from headhunter_backend.db.models import Vacancy
from typing import Sequence

ws_router: APIRouter = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger(__name__)


@ws_router.websocket("/vacancies")
async def websocket_vacancies(websocket: WebSocket, session: SessionDep) -> None:
    await websocket.accept()
    vacancies: Sequence[Vacancy] = await list_vacancies(session=session)
    for vacancy in vacancies:
        event: VacancyEvent = VacancyEvent(data=vacancy_to_model(row=vacancy))
        await websocket.send_json(data=event.model_dump(mode="json"))
    await websocket.close()


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
