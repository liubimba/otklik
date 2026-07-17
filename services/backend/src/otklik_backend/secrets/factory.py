from pathlib import Path

from keyring.backend import KeyringBackend

from otklik_backend.log import get_logger
from otklik_backend.secrets.file_store import FileSecretStore
from otklik_backend.secrets.keyring_store import KeyringSecretStore
from otklik_backend.secrets.store import SecretStore

PROBE_ACCOUNT = "__probe__"


class SecretStoreFactory:
    def __init__(
        self, backend: KeyringBackend | None = None, file_path: Path | None = None
    ) -> None:
        self._backend = backend
        self._file_path = file_path
        self._log = get_logger(self.__class__.__name__)

    async def create(self) -> SecretStore:
        keychain = KeyringSecretStore(backend=self._backend)
        try:
            await keychain.get(PROBE_ACCOUNT)
        except Exception as e:
            self._log.warning(
                "Системная связка ключей недоступна (%s) — ключи будут храниться "
                "в файле ~/.otklik/secrets.json (0600). Это менее безопасно.",
                e,
            )
            return FileSecretStore(path=self._file_path)
        return keychain
