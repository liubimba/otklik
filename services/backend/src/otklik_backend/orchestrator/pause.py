import asyncio


class PauseController:
    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._event.set()

    def pause(self) -> None:
        self._event.clear()

    def resume(self) -> None:
        self._event.set()

    def is_paused(self) -> bool:
        return not self._event.is_set()

    async def wait(self) -> None:
        await self._event.wait()
