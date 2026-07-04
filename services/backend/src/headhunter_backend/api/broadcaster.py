import asyncio
from pydantic import BaseModel
from headhunter_backend.log import get_logger
from headhunter_backend.api.subscribers import EventSubscriberInterface


class EventBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[EventSubscriberInterface] = set()
        self._pending: set[asyncio.Task[None]] = set()
        self._logger = get_logger(self.__class__.__name__)

    def register(self, subscriber: EventSubscriberInterface) -> None:
        self._logger.info(f"Registering subscriber: {subscriber}")
        self._subscribers.add(subscriber)

    def unregister(self, subscriber: EventSubscriberInterface) -> None:
        self._logger.info(f"Unregistering subscriber: {subscriber}")
        self._subscribers.discard(subscriber)

    async def publish(self, event: BaseModel) -> None:
        payload = event.model_dump()
        if payload.get("type") is None:
            raise ValueError("Event type is required")
        if payload.get("data") is None:
            raise ValueError("Event data is required")
        self._logger.info(f"Publishing event: {payload}")
        for subscriber in list(self._subscribers):
            task = asyncio.create_task(
                self._deliver(subscriber=subscriber, event=event)
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

    async def _deliver(
        self, subscriber: EventSubscriberInterface, event: BaseModel
    ) -> None:
        try:
            await subscriber.accept(event=event)
        except Exception as e:
            self._logger.warning(
                f"Subscriber {subscriber} raised, unregistering: {e!r}"
            )
            self.unregister(subscriber=subscriber)
