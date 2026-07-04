import asyncio

from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.core.events import AuthWSEvent
from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.core.site import SiteAuthFlow
from headhunter_backend.log import get_logger


class AuthorizationService:
    def __init__(self, broadcaster: EventBroadcaster, auth_flow: SiteAuthFlow) -> None:
        self._broadcaster = broadcaster
        self._auth_flow = auth_flow
        self._log = get_logger(__name__)
        self._task: asyncio.Task[None] | None = None

    async def status(self) -> AuthStatusAPISchema:
        return await self._auth_flow.get_auth_status()

    async def authorize(self) -> AuthStatusAPISchema:
        authorizing = AuthStatusAPISchema.authorizing()
        self._task = asyncio.create_task(self._wait_and_announce())
        await self._broadcaster.publish(event=AuthWSEvent(data=authorizing))
        # Report the state we just entered — auth is now in-flight. The
        # real browser status is still `unauthorized` until
        # `_wait_and_announce` completes, but the HTTP caller (and the WS
        # event above) must see `authorizing` so the UI can show progress.
        return authorizing

    async def unauthorize(self) -> AuthStatusAPISchema:
        await self._auth_flow.unauthorize()
        await self._broadcaster.publish(
            event=AuthWSEvent(data=await self._auth_flow.get_auth_status())
        )
        return await self.status()

    async def cancel(self) -> AuthStatusAPISchema:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._broadcaster.publish(
            event=AuthWSEvent(data=await self._auth_flow.get_auth_status())
        )
        return await self.status()

    async def _wait_and_announce(self) -> None:
        try:
            await self._auth_flow.wait_for_login()
        finally:
            await self._broadcaster.publish(
                event=AuthWSEvent(data=await self._auth_flow.get_auth_status())
            )
