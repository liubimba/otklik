import logging
from typing import Any
import structlog
from rich.traceback import install as install_rich_traceback

from structlog.typing import EventDict, WrappedLogger


def fold_logger_name(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    name = event_dict.pop("logger", None) or event_dict.pop("logger_name", None)
    if name is not None:
        event_dict["event"] = f"[{name}] {event_dict.get('event', '')}"
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    install_rich_traceback(show_locals=False)
    logging.basicConfig(format="%(message)s", level=level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.processors.add_log_level,
            fold_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True, pad_level=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("patchright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name)
