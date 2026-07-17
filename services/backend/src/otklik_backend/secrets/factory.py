from pathlib import Path

from keyring.backend import KeyringBackend

from otklik_backend.log import get_logger
from otklik_backend.secrets.file_store import FileSecretStore
from otklik_backend.secrets.keyring_store import KeyringSecretStore
from otklik_backend.secrets.store import SecretStore

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
        except Exception as e:
            # Ловим всё, а не только SecretStoreUnavailableError: проба — это
            # вызов чужого кода (keyring-бэкенд, D-Bus, pywin32-ctypes), и он
            # волен бросить что угодно своё. Любое исключение здесь означает
            # ровно одно — на связку нельзя положиться, и выбор фолбэка не
            # должен зависеть от того, догадались ли мы обернуть конкретный
            # тип. Выпустить незнакомое исключение наружу = уронить старт
            # бэкенда там, где есть рабочий фолбэк.
            self._log.warning(
                "Системная связка ключей недоступна (%s) — ключи будут храниться "
                "в файле ~/.otklik/secrets.json (0600). Это менее безопасно.",
                e,
            )
            return FileSecretStore(path=self._file_path)
        return keychain
