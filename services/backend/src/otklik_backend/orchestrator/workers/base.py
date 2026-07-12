import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.core.state import ProcessingState
from otklik_backend.db.repositories.applications import ApplicationRepository
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

    async def recover(self, session: AsyncSession) -> int:
        applications = await ApplicationRepository.list_by_status(
            session=session, status=self.handled_status
        )
        for application in applications:
            await self.enqueue(application_id=application.id)
        return len(applications)

    @abstractmethod
    async def _process_one(self, application_id: int) -> None: ...
