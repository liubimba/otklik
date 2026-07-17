import asyncio
import json
import os
from pathlib import Path
from typing import Any

from otklik_backend.log import get_logger
from otklik_backend.paths import AppPaths
from otklik_backend.secrets.store import SecretStorageMode

SECRETS_FILE_NAME = "secrets.json"


class FileSecretStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (AppPaths().root / SECRETS_FILE_NAME)
        self._log = get_logger(self.__class__.__name__)

    @property
    def mode(self) -> SecretStorageMode:
        return SecretStorageMode.FILE

    async def get(self, account: str) -> str | None:
        items = await asyncio.to_thread(self._read)
        value = items.get(account)
        return str(value) if value is not None else None

    async def set(self, account: str, secret: str) -> None:
        await asyncio.to_thread(self._mutate, account, secret)

    async def delete(self, account: str) -> None:
        await asyncio.to_thread(self._mutate, account, None)

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            loaded: Any = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self._log.error("Secrets file is unreadable", error=str(error))
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _mutate(self, account: str, secret: str | None) -> None:
        items = self._read()
        if secret is None:
            items.pop(account, None)
        else:
            items[account] = secret
        self._write(items)

    def _write(self, items: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False)
        os.chmod(self._path, 0o600)
