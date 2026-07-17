import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from otklik_backend.browser.chromium_gate import ChromiumGate, ChromiumInstallError


class _FakeProcess:
    returncode = 1

    def __init__(self) -> None:
        self.stdout = self

    def __aiter__(self) -> Any:
        return self

    async def __anext__(self) -> bytes:
        raise StopAsyncIteration

    async def wait(self) -> int:
        return 1


BASIC_PROGRESS_LINE = "|■■■■■■■■                | 40% of 164.9 MiB"


def test_parses_percent_and_total_from_the_patchright_progress_line() -> None:
    progress = ChromiumGate.parse_progress(BASIC_PROGRESS_LINE)
    assert progress is not None
    assert progress.percent == 40.0
    assert progress.total_bytes == int(164.9 * 1024 * 1024)
    assert progress.done is False


def test_parses_a_zero_percent_line() -> None:
    progress = ChromiumGate.parse_progress(
        "|                        |  0% of 164.9 MiB"
    )
    assert progress is not None
    assert progress.percent == 0.0


def test_hundred_percent_is_not_done_until_the_process_exits() -> None:
    progress = ChromiumGate.parse_progress(
        "|■■■■■■■■■■■■■■■■■■■■■■■■| 100% of 164.9 MiB"
    )
    assert progress is not None
    assert progress.percent == 100.0
    assert progress.done is False


def test_ignores_lines_that_carry_no_progress() -> None:
    assert (
        ChromiumGate.parse_progress("Downloading Chromium 133.0 from https://x") is None
    )
    assert ChromiumGate.parse_progress("") is None


async def test_install_runs_the_patchright_node_driver_not_the_python_executable(
    tmp_path: Path,
) -> None:
    spawned: dict[str, Any] = {}

    async def fake_exec(*argv: str, **kwargs: Any) -> Any:
        spawned["argv"] = argv
        spawned["env"] = kwargs["env"]
        return _FakeProcess()

    gate = ChromiumGate(browsers_dir=tmp_path)
    with patch("asyncio.create_subprocess_exec", fake_exec):
        with pytest.raises(ChromiumInstallError):
            async for _ in gate.install():
                pass

    assert spawned["argv"][0] != sys.executable
    assert spawned["argv"][0].endswith("node")
    assert spawned["argv"][1].endswith("cli.js")
    assert spawned["argv"][2:] == ("install", "chromium")
    assert spawned["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)
