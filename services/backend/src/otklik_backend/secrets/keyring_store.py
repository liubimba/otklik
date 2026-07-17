import asyncio

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from otklik_backend.log import get_logger
from otklik_backend.secrets.store import (
    SERVICE_NAME,
    SecretStorageMode,
    SecretStoreUnavailableError,
)


class KeyringSecretStore:
    def __init__(self, backend: KeyringBackend | None = None) -> None:
        self._backend: KeyringBackend = backend or keyring.get_keyring()
        self._log = get_logger(self.__class__.__name__)

    @property
    def mode(self) -> SecretStorageMode:
        return SecretStorageMode.KEYCHAIN

    async def get(self, account: str) -> str | None:
        try:
            return await asyncio.to_thread(
                self._backend.get_password, SERVICE_NAME, account
            )
        except KeyringError as error:
            raise self._unavailable(error) from error

    async def set(self, account: str, secret: str) -> None:
        try:
            await asyncio.to_thread(
                self._backend.set_password, SERVICE_NAME, account, secret
            )
        except KeyringError as error:
            raise self._unavailable(error) from error

    async def delete(self, account: str) -> None:
        try:
            await asyncio.to_thread(
                self._backend.delete_password, SERVICE_NAME, account
            )
        except (PasswordDeleteError, KeyError):
            return
        except KeyringError as error:
            raise self._unavailable(error) from error

    def _unavailable(self, error: KeyringError) -> SecretStoreUnavailableError:
        self._log.error("Keyring call failed", error=str(error))
        return SecretStoreUnavailableError()
