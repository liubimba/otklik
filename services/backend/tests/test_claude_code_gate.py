from pathlib import Path
from unittest.mock import patch

from otklik_backend.setup.claude_code import ClaudeCodeGate, ClaudeCodeState


def _gate(tmp_path: Path, *, creds: bool) -> ClaudeCodeGate:
    creds_file = tmp_path / ".credentials.json"
    if creds:
        creds_file.write_text("{}")
    return ClaudeCodeGate(credentials_file=creds_file)


async def test_not_installed_when_binary_missing(tmp_path: Path) -> None:
    with patch(
        "otklik_backend.setup.claude_code.resolve_claude_binary", return_value=None
    ):
        gate = _gate(tmp_path, creds=True)
        assert await gate.state() == ClaudeCodeState.NOT_INSTALLED


async def test_not_authed_when_binary_present_but_no_creds(tmp_path: Path) -> None:
    with patch(
        "otklik_backend.setup.claude_code.resolve_claude_binary",
        return_value="/usr/bin/claude",
    ):
        gate = _gate(tmp_path, creds=False)
        assert await gate.state() == ClaudeCodeState.NOT_AUTHED


async def test_ready_when_binary_and_creds_present(tmp_path: Path) -> None:
    with patch(
        "otklik_backend.setup.claude_code.resolve_claude_binary",
        return_value="/usr/bin/claude",
    ):
        gate = _gate(tmp_path, creds=True)
        assert await gate.state() == ClaudeCodeState.READY


def test_credentials_present_reflects_file(tmp_path: Path) -> None:
    gate_with_creds = ClaudeCodeGate(credentials_file=tmp_path / "with_creds.json")
    (tmp_path / "with_creds.json").write_text("{}")
    assert gate_with_creds.credentials_present() is True

    gate_without_creds = ClaudeCodeGate(
        credentials_file=tmp_path / "without_creds.json"
    )
    assert gate_without_creds.credentials_present() is False
