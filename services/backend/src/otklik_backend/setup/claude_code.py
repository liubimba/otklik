from enum import Enum
from pathlib import Path

from otklik_backend.ai.claude_code import resolve_claude_binary

DEFAULT_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"


class ClaudeCodeState(str, Enum):
    NOT_INSTALLED = "not_installed"  # бинарник `claude` не найден
    NOT_AUTHED = "not_authed"  # бинарник есть, но файла кредов нет
    READY = "ready"  # бинарник + файл кредов на месте


class ClaudeCodeGate:
    """Дешёвый детект того, что CLI Claude Code пригоден к работе.

    Содержимое файла кредов НЕ читаем — сам факт его наличия и есть сигнал
    «залогинен». Реальную валидность токена (протухание) доказывает уже
    генерация-триал, а не этот гейт."""

    def __init__(self, credentials_file: Path = DEFAULT_CREDENTIALS_FILE) -> None:
        self._credentials_file = credentials_file

    async def state(self) -> ClaudeCodeState:
        if resolve_claude_binary() is None:
            return ClaudeCodeState.NOT_INSTALLED
        if not self._credentials_file.exists():
            return ClaudeCodeState.NOT_AUTHED
        return ClaudeCodeState.READY

    def credentials_present(self) -> bool:
        """Сигнал видимости карточки для /setup/state: существует ли файл
        кредов вообще (независимо от бинарника CLI)."""
        return self._credentials_file.exists()
