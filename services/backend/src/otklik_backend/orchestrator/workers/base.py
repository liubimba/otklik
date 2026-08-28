import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar, Sequence

from otklik_backend.core.state import ProcessingState
from otklik_backend.log import get_logger


class Worker(ABC):
    handled_status: ClassVar[ProcessingState]

    def __init__(self) -> None:
        self._log = get_logger(self.__class__.__name__)
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._pending: list[int] = []
        self._once = False

    async def enqueue(self, application_id: int) -> None:
        await self._queue.put(application_id)
        self._pending.append(application_id)

    async def get_next(self) -> int:
        application_id = await self._queue.get()
        try:
            self._pending.remove(application_id)
        except ValueError:
            pass
        return application_id

    def qsize(self) -> int:
        return self._queue.qsize()

    def get_application_ids(self) -> Sequence[int]:
        return list(self._pending)

    def clear(self) -> list[int]:
        dropped: list[int] = []
        while True:
            try:
                dropped.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        self._pending.clear()
        return dropped

    @abstractmethod
    async def _process_one(self, application_id: int) -> bool: ...
