import asyncio
import os
import sys
from pathlib import Path

from otklik_backend.log import get_logger


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

    async def install(self) -> None:
        self._browsers_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, **self.driver_env()}
        self._log.info("Downloading Chromium", path=str(self._browsers_dir))
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "patchright",
            "install",
            "chromium",
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await process.communicate()
        if process.returncode != 0:
            raise ChromiumInstallError(output.decode(errors="replace")[-2000:])
        self._log.info("Chromium ready", path=str(self._browsers_dir))
