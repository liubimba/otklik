from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class Runnable(Protocol):
    async def run(self) -> None: ...


@runtime_checkable
class Recoverable(Protocol):
    async def recover(self, session: AsyncSession) -> int: ...


@runtime_checkable
class EventListener(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...
