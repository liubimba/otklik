from enum import Enum
from pathlib import Path

from otklik_backend.ai.claude_code import resolve_claude_binary

DEFAULT_CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"


class ClaudeCodeState(str, Enum):
    NOT_INSTALLED = "not_installed"
    NOT_AUTHED = "not_authed"
    READY = "ready"


class ClaudeCodeGate:
    def __init__(self, credentials_file: Path = DEFAULT_CREDENTIALS_FILE) -> None:
        self._credentials_file = credentials_file

    async def state(self) -> ClaudeCodeState:
        if resolve_claude_binary() is None:
            return ClaudeCodeState.NOT_INSTALLED
        if not self._credentials_file.exists():
            return ClaudeCodeState.NOT_AUTHED
        return ClaudeCodeState.READY

    def credentials_present(self) -> bool:
        return self._credentials_file.exists()
