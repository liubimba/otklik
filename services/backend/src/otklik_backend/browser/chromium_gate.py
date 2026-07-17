import asyncio
import re
from collections.abc import AsyncIterator
from pathlib import Path

from patchright._impl._driver import compute_driver_executable, get_driver_env

from otklik_backend.core.progress import PullProgress
from otklik_backend.log import get_logger

PROGRESS_LINE = re.compile(r"\|\s*(\d+)%\s+of\s+([\d.]+)\s*MiB")


class ChromiumInstallError(Exception): ...


class ChromiumGate:
    def __init__(self, browsers_dir: Path) -> None:
        self._browsers_dir = browsers_dir
        self._log = get_logger(self.__class__.__name__)

    def is_installed(self) -> bool:
        if not self._browsers_dir.is_dir():
            return False
        return any(
            entry.name.startswith("chromium-") for entry in self._browsers_dir.iterdir()
        )

    def driver_env(self) -> dict[str, str]:
        return {"PLAYWRIGHT_BROWSERS_PATH": str(self._browsers_dir)}

    @staticmethod
    def parse_progress(line: str) -> PullProgress | None:
        match = PROGRESS_LINE.search(line)
        if match is None:
            return None
        percent = float(match.group(1))
        total_bytes = int(float(match.group(2)) * 1024 * 1024)
        return PullProgress(
            status="downloading",
            completed_bytes=int(total_bytes * percent / 100),
            total_bytes=total_bytes,
            percent=percent,
            done=False,
        )

    async def install(self) -> AsyncIterator[PullProgress]:
        self._browsers_dir.mkdir(parents=True, exist_ok=True)
        yield PullProgress(status="starting")
        node, cli = compute_driver_executable()
        process = await asyncio.create_subprocess_exec(
            node,
            cli,
            "install",
            "chromium",
            env={**get_driver_env(), **self.driver_env()},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        tail: list[str] = []
        assert process.stdout is not None
        async for raw in process.stdout:
            line = raw.decode(errors="replace").rstrip()
            tail = [*tail[-40:], line]
            progress = self.parse_progress(line)
            if progress is not None:
                yield progress
        if await process.wait() != 0:
            raise ChromiumInstallError("\n".join(tail)[-2000:])
        if not self.is_installed():
            raise ChromiumInstallError(
                f"patchright finished but no chromium-* directory appeared in {self._browsers_dir}"
            )
        self._log.info("Chromium ready", path=str(self._browsers_dir))
        yield PullProgress(status="done", percent=100.0, done=True)
