import logging
import logging.handlers
import queue

from otklik_backend.log import DroppingQueueHandler, configure_logging


def test_dropping_queue_handler_drops_instead_of_blocking_when_full() -> None:
    q: queue.Queue = queue.Queue(maxsize=1)
    q.put_nowait(object())
    handler = DroppingQueueHandler(q)
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="p",
        lineno=1,
        msg="blocked sink must not stall the caller",
        args=None,
        exc_info=None,
    )

    handler.emit(record)

    assert q.qsize() == 1


def test_configure_logging_routes_root_through_a_queue_handler() -> None:
    configure_logging()
    root = logging.getLogger()
    assert any(isinstance(h, logging.handlers.QueueHandler) for h in root.handlers)


def test_configure_logging_keeps_uvicorn_loggers_off_their_own_blocking_handlers() -> (
    None
):
    configure_logging()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert logging.getLogger(name).handlers == []
