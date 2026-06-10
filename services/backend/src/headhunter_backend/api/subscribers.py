from pydantic import BaseModel
from fastapi import WebSocket
from typing import Self, Callable, Awaitable


class EventSubscriberInterface:
    async def accept(self, event: BaseModel) -> None:
        pass


class WSEventSubscriber(EventSubscriberInterface):
    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws

    async def accept(self, event: BaseModel) -> None:
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
