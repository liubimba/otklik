from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from headhunter_backend.api.dependencies import BroadcasterDep
from headhunter_backend.log import get_logger
from headhunter_backend.api.events import VacancyWSEvent
from headhunter_backend.db.crud import list_vacancies
from headhunter_backend.api.dependencies import SessionDep
from headhunter_backend.db.converters import vacancy_to_schema
from headhunter_backend.db.models import VacancyORM
from typing import Sequence
from headhunter_backend.api.subscribers import WSEventSubscriber

ws_router: APIRouter = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger(__name__)


@ws_router.websocket("/vacancies")
async def websocket_vacancies(websocket: WebSocket, session: SessionDep) -> None:
    await websocket.accept()
    vacancies: Sequence[VacancyORM] = await list_vacancies(session=session)
    for vacancy in vacancies:
        event: VacancyWSEvent = VacancyWSEvent(data=vacancy_to_schema(row=vacancy))
        await websocket.send_json(data=event.model_dump(mode="json"))
    await websocket.close()


@ws_router.websocket("/events")
async def websocket_events(websocket: WebSocket, broadcaster: BroadcasterDep) -> None:
    await websocket.accept()
    logger.info("WebSocket connection established on /ws/events")
    subscriber: WSEventSubscriber = WSEventSubscriber.from_websocket(ws=websocket)
    broadcaster.register(subscriber=subscriber)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket disconnected. Reason: {e.reason}")
    finally:
        broadcaster.unregister(subscriber=subscriber)
    logger.info("WebSocket connection closed on /ws/events")
