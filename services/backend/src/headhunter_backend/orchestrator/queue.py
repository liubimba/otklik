import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from headhunter_backend.log import get_logger
from headhunter_backend.db.crud import list_active_applications
from headhunter_backend.db.models import Application
from typing import Sequence


class Orchestrator:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._log = get_logger(__name__)

    async def enqueue(self, application_id: int) -> None:
        await self._queue.put(application_id)

    async def get_next(self) -> int:
        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()

    async def recover_from_db(self, session: AsyncSession) -> int:
        applications: Sequence[Application] = await list_active_applications(session)
        for application in applications:
            await self.enqueue(application_id=application.id)
        return len(applications)
