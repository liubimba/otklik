from pathlib import Path

import pytest
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError

from otklik_backend.secrets.factory import SecretStoreFactory
from otklik_backend.secrets.file_store import FileSecretStore
from otklik_backend.secrets.keyring_store import KeyringSecretStore
from otklik_backend.secrets.store import (
    SecretStorageMode,
    SecretStoreUnavailableError,
    account_for,
)


class _MemoryBackend(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.items.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.items[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        del self.items[(service, username)]


class _BrokenBackend(KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringError("no backend")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringError("no backend")

    def delete_password(self, service: str, username: str) -> None:
        raise KeyringError("no backend")


def test_account_for_is_namespaced() -> None:
    assert account_for("abc123") == "llm.deployment.abc123"


async def test_keyring_store_round_trips() -> None:
    store = KeyringSecretStore(backend=_MemoryBackend())
    assert store.mode is SecretStorageMode.KEYCHAIN
    assert await store.get("acct") is None
    await store.set("acct", "sk-secret")
    assert await store.get("acct") == "sk-secret"
    await store.delete("acct")
    assert await store.get("acct") is None


async def test_keyring_store_delete_is_idempotent() -> None:
    store = KeyringSecretStore(backend=_MemoryBackend())
    await store.delete("never-existed")


async def test_keyring_store_translates_backend_failure() -> None:
    store = KeyringSecretStore(backend=_BrokenBackend())
    with pytest.raises(SecretStoreUnavailableError):
        await store.set("acct", "sk-secret")


async def test_file_store_round_trips_and_is_private(tmp_path: Path) -> None:
    path = tmp_path / "secrets.json"
    store = FileSecretStore(path=path)
    assert store.mode is SecretStorageMode.FILE
    assert await store.get("acct") is None
    await store.set("acct", "sk-secret")
    assert await store.get("acct") == "sk-secret"
    assert path.stat().st_mode & 0o777 == 0o600
    await store.delete("acct")
    assert await store.get("acct") is None


async def test_file_store_keeps_other_accounts(tmp_path: Path) -> None:
    store = FileSecretStore(path=tmp_path / "secrets.json")
    await store.set("a", "sk-a")
    await store.set("b", "sk-b")
    await store.delete("a")
    assert await store.get("a") is None
    assert await store.get("b") == "sk-b"


async def test_file_store_missing_file_reads_as_empty(tmp_path: Path) -> None:
    store = FileSecretStore(path=tmp_path / "nope.json")
    assert await store.get("acct") is None


async def test_file_store_delete_is_idempotent(tmp_path: Path) -> None:
    store = FileSecretStore(path=tmp_path / "secrets.json")
    await store.delete("never-existed")


async def test_factory_falls_back_to_file_without_keychain(tmp_path: Path) -> None:
    factory = SecretStoreFactory(
        backend=_BrokenBackend(), file_path=tmp_path / "secrets.json"
    )
    store = await factory.create()
    assert store.mode is SecretStorageMode.FILE


async def test_factory_prefers_keychain_when_available(tmp_path: Path) -> None:
    factory = SecretStoreFactory(
        backend=_MemoryBackend(), file_path=tmp_path / "secrets.json"
    )
    store = await factory.create()
    assert store.mode is SecretStorageMode.KEYCHAIN
