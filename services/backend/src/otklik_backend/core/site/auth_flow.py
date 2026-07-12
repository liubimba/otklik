from typing import Protocol, runtime_checkable

from otklik_backend.api.schemas import AuthStatusAPISchema


@runtime_checkable
class SiteAuthFlow(Protocol):
    async def get_auth_status(self) -> AuthStatusAPISchema: ...

    async def wait_for_login(self, poll_interval: float = 1.0) -> None: ...

    async def unauthorize(self) -> None: ...
