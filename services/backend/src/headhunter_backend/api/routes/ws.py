from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from headhunter_backend.api.dependencies import BroadcasterDep
from headhunter_backend.api.subscribers import WSEventSubscriber
from headhunter_backend.log import get_logger

ws_router: APIRouter = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger(__name__)


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
