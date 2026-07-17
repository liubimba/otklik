from enum import Enum
from typing import Protocol, runtime_checkable

from otklik_backend.core.exceptions import ServiceUnavailableError

SERVICE_NAME = "ai.otklik.app"


def account_for(deployment_id: str) -> str:
    return f"llm.deployment.{deployment_id}"


class SecretStorageMode(str, Enum):
    KEYCHAIN = "keychain"
    FILE = "file"


class SecretStoreUnavailableError(ServiceUnavailableError):
    detail = "Хранилище ключей недоступно"
    code = "SECRET_STORE_UNAVAILABLE"


@runtime_checkable
class SecretStore(Protocol):
    @property
    def mode(self) -> SecretStorageMode: ...

    async def get(self, account: str) -> str | None: ...

    async def set(self, account: str, secret: str) -> None: ...

    async def delete(self, account: str) -> None: ...
