import logging
import logging.handlers
import queue
from typing import Any
import structlog
from rich.traceback import install as install_rich_traceback

from structlog.typing import EventDict, WrappedLogger

LOG_QUEUE_SIZE = 20000
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

_listener: logging.handlers.QueueListener | None = None


class DroppingQueueHandler(logging.handlers.QueueHandler):
    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            pass


def fold_logger_name(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    name = event_dict.pop("logger", None) or event_dict.pop("logger_name", None)
    if name is not None:
        event_dict["event"] = f"[{name}] {event_dict.get('event', '')}"
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    global _listener
    install_rich_traceback(show_locals=False)

    log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=LOG_QUEUE_SIZE)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))

    if _listener is not None:
        _listener.stop()
    _listener = logging.handlers.QueueListener(
        log_queue, stream_handler, respect_handler_level=True
    )
    _listener.start()

    root = logging.getLogger()
    root.handlers = [DroppingQueueHandler(log_queue)]
    root.setLevel(level)

    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

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
