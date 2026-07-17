import os
import sys
from unittest.mock import AsyncMock, patch

from otklik_backend.api.app import app, run, start_browser_best_effort
from otklik_backend.paths import AppPaths


def test_run_passes_the_requested_port_to_uvicorn() -> None:
    with patch("uvicorn.run") as uvicorn_run:
        run(port=12345)
    kwargs = uvicorn_run.call_args.kwargs
    assert kwargs["port"] == 12345
    assert kwargs["host"] == "127.0.0.1"


def test_run_hands_uvicorn_the_app_object_not_an_import_string() -> None:
    with patch("uvicorn.run") as uvicorn_run:
        run(port=12345)
    assert uvicorn_run.call_args.args[0] is app


def test_cli_reads_port_from_argv() -> None:
    from otklik_backend.api.app import main

    with patch.dict(os.environ, {}, clear=False):
        with patch("uvicorn.run") as uvicorn_run:
            with patch.object(sys, "argv", ["otklik-backend", "--port", "23456"]):
                main()
    assert uvicorn_run.call_args.kwargs["port"] == 23456


async def test_startup_survives_a_browser_whose_chromium_is_not_installed() -> None:
    browser = AsyncMock()
    browser.start.side_effect = RuntimeError("Executable doesn't exist at chrome")
    await start_browser_best_effort(browser=browser)
    browser.start.assert_awaited_once()


async def test_startup_starts_the_browser_when_chromium_is_present() -> None:
    browser = AsyncMock()
    await start_browser_best_effort(browser=browser)
    browser.start.assert_awaited_once()


def test_cli_points_the_patchright_driver_at_the_app_data_dir() -> None:
    from otklik_backend.api.app import main

    with patch.dict(os.environ, {}, clear=False):
        with patch("uvicorn.run"):
            with patch.object(sys, "argv", ["otklik-backend"]):
                main()
            assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(
                AppPaths().browsers_dir
            )
    assert "PLAYWRIGHT_BROWSERS_PATH" not in os.environ
