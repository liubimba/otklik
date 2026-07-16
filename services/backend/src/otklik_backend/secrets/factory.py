from pathlib import Path

from keyring.backend import KeyringBackend

from otklik_backend.log import get_logger
from otklik_backend.secrets.file_store import FileSecretStore
from otklik_backend.secrets.keyring_store import KeyringSecretStore
from otklik_backend.secrets.store import SecretStore, SecretStoreUnavailableError

PROBE_ACCOUNT = "__probe__"


class SecretStoreFactory:
    """Единственное место, где решается, где живут ключи. Режим выбирается один
    раз на старте и дальше не меняется: иначе миграция и предупреждение в UI
    могли бы разойтись между собой."""

    def __init__(
        self, backend: KeyringBackend | None = None, file_path: Path | None = None
    ) -> None:
        self._backend = backend
        self._file_path = file_path
        self._log = get_logger(self.__class__.__name__)

    async def create(self) -> SecretStore:
        keychain = KeyringSecretStore(backend=self._backend)
        try:
            # Живая проба, а не догадка по списку бэкендов: на Linux связка
            # может «быть» и при этом падать без D-Bus-сессии.
            await keychain.get(PROBE_ACCOUNT)
        except SecretStoreUnavailableError:
            self._log.warning(
                "Системная связка ключей недоступна — ключи будут храниться в "
                "файле ~/.otklik/secrets.json (0600). Это менее безопасно."
            )
            return FileSecretStore(path=self._file_path)
        return keychain
