import asyncio
from typing import Mapping

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.schemas import AuthStatusAPISchema
from otklik_backend.core.board import DEFAULT_BOARD, Board
from otklik_backend.core.events import AuthWSEvent
from otklik_backend.core.site import SiteAuthFlow
from otklik_backend.log import get_logger


class AuthorizationService:
    def __init__(
        self,
        broadcaster: EventBroadcaster,
        auth_flows: Mapping[Board, SiteAuthFlow],
    ) -> None:
        self._broadcaster = broadcaster
        self._auth_flows = auth_flows
        self._log = get_logger(__name__)
        self._tasks: dict[Board, asyncio.Task[None]] = {}

    def _flow(self, board: Board) -> SiteAuthFlow:
        return self._auth_flows[board]

    async def status(self, board: Board = DEFAULT_BOARD) -> AuthStatusAPISchema:
        return await self._flow(board).get_auth_status()

    async def authorize(self, board: Board = DEFAULT_BOARD) -> AuthStatusAPISchema:
        authorizing = AuthStatusAPISchema.authorizing()
        self._tasks[board] = asyncio.create_task(self._wait_and_announce(board))
        await self._broadcaster.publish(event=AuthWSEvent(data=authorizing))
        return authorizing

    async def unauthorize(self, board: Board = DEFAULT_BOARD) -> AuthStatusAPISchema:
        await self._flow(board).unauthorize()
        await self._broadcaster.publish(
            event=AuthWSEvent(data=await self._flow(board).get_auth_status())
        )
        return await self.status(board)

    async def cancel(self, board: Board = DEFAULT_BOARD) -> AuthStatusAPISchema:
        task = self._tasks.get(board)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._broadcaster.publish(
            event=AuthWSEvent(data=await self._flow(board).get_auth_status())
        )
        return await self.status(board)

    async def _wait_and_announce(self, board: Board) -> None:
        try:
            await self._flow(board).wait_for_login()
        finally:
            await self._broadcaster.publish(
                event=AuthWSEvent(data=await self._flow(board).get_auth_status())
            )
