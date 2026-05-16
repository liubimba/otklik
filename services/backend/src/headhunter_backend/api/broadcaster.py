from fastapi import WebSocket
from pydantic import BaseModel
from headhunter_backend.log import get_logger


class EventBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[WebSocket] = set()
        self._logger = get_logger(self.__class__.__name__)

    def register(self, ws: WebSocket) -> None:
        self._logger.info(f"Registering WebSocket: {ws.client}")
        self._subscribers.add(ws)

    def unregister(self, ws: WebSocket) -> None:
        self._logger.info(f"Unregistering WebSocket: {ws.client}")
        self._subscribers.discard(ws)

    async def publish(self, event: BaseModel) -> None:
        if event.model_dump().get("type") is None:
            raise ValueError("Event must have a 'type' field")
        if event.model_dump().get("data") is None:
            raise ValueError("Event must have a 'data' field")
        self._logger.info(f"Publishing event: {event.model_dump()}")
        dead: list[WebSocket] = []
        for ws in self._subscribers:
            try:
                await ws.send_text(event.model_dump_json())
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.unregister(ws)
