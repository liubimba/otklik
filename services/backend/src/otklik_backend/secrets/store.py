from enum import Enum
from typing import Protocol, runtime_checkable

from otklik_backend.core.exceptions import ServiceUnavailableError

# Совпадает с identifier из apps/desktop/src-tauri/tauri.conf.json.
SERVICE_NAME = "ai.otklik.app"


def account_for(deployment_id: str) -> str:
    """Имя аккаунта в хранилище для конкретного deployment'а."""
    return f"llm.deployment.{deployment_id}"


class SecretStorageMode(str, Enum):
    KEYCHAIN = "keychain"  # системная связка — нормальный режим
    FILE = "file"  # связки в системе нет: ~/.otklik/secrets.json, 0600


class SecretStoreUnavailableError(ServiceUnavailableError):
    detail = "Хранилище ключей недоступно"
    code = "SECRET_STORE_UNAVAILABLE"


@runtime_checkable
class SecretStore(Protocol):
    """Где живут секреты. Async намеренно: keyring синхронный, а заблокированная
    связка на macOS ждёт модалку — синхронный вызов заморозил бы весь event loop."""

    @property
    def mode(self) -> SecretStorageMode: ...

    async def get(self, account: str) -> str | None: ...

    async def set(self, account: str, secret: str) -> None: ...

    async def delete(self, account: str) -> None:
        """Идемпотентно: удаление отсутствующего секрета — не ошибка."""
        ...
