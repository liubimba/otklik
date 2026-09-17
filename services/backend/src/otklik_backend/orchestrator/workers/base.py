import asyncio
from abc import ABC, abstractmethod
from collections import deque
from typing import ClassVar, Sequence

from otklik_backend.core.state import ProcessingState
from otklik_backend.log import get_logger


class Worker(ABC):
    handled_status: ClassVar[ProcessingState]

    def __init__(self) -> None:
        self._log = get_logger(self.__class__.__name__)
        self._queue: deque[int] = deque()
        self._pending: list[int] = []
        self._available = asyncio.Event()
        self._once = False

    async def enqueue(self, application_id: int) -> None:
        self._queue.append(application_id)
        self._pending.append(application_id)
        self._available.set()

    async def enqueue_front(self, application_id: int) -> None:
        self._queue.appendleft(application_id)
        self._pending.append(application_id)
        self._available.set()

    async def get_next(self) -> int:
        while not self._queue:
            self._available.clear()
            if not self._queue:
                await self._available.wait()
        application_id = self._queue.popleft()
        try:
            self._pending.remove(application_id)
        except ValueError:
            pass
        return application_id

    def qsize(self) -> int:
        return len(self._queue)

    def get_application_ids(self) -> Sequence[int]:
        return list(self._pending)

    def clear(self) -> list[int]:
        dropped = list(self._queue)
        self._queue.clear()
        self._pending.clear()
        self._available.clear()
        return dropped

    @abstractmethod
    async def _process_one(self, application_id: int) -> bool: ...
