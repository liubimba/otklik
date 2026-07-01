from pydantic import BaseModel
from fastapi import WebSocket
from typing import Self, Callable, Awaitable
from headhunter_backend.log import get_logger


class EventSubscriberInterface:
    async def accept(self, event: BaseModel) -> None:
        pass


class WSEventSubscriber(EventSubscriberInterface):
    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws
        self._log = get_logger(self.__class__.__name__)

    async def accept(self, event: BaseModel) -> None:
        self._log.info("Received event", payload=event.model_dump_json())
        await self._ws.send_text(event.model_dump_json())

    @classmethod
    def from_websocket(cls, ws: WebSocket) -> Self:
        return cls(ws)


class CallbackEventSubscriber(EventSubscriberInterface):
    def __init__(self, callback: Callable[[BaseModel], Awaitable[None]]):
        self._callback = callback

    async def accept(self, event: BaseModel) -> None:
        await self._callback(event)

    @classmethod
    def from_callback(cls, callback: Callable[[BaseModel], Awaitable[None]]) -> Self:
        return cls(callback)
