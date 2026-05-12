import logging
from typing import Any
import structlog
from rich.traceback import install as install_rich_traceback


def configure_logging(level: int = logging.INFO) -> None:
    install_rich_traceback(show_locals=False)
    logging.basicConfig(format="%(message)s", level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("patchright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
