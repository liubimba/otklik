import asyncio
from typing import Literal

import pytest
from pydantic import BaseModel

from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.api.subscribers import CallbackEventSubscriber


class _DummyData(BaseModel):
    value: int


class _DummyEvent(BaseModel):
    type: Literal["dummy"] = "dummy"
    data: _DummyData


async def _drain(broadcaster: EventBroadcaster) -> None:
    """Wait for all fire-and-forget delivery tasks to finish."""
    while broadcaster._pending:
        pending = list(broadcaster._pending)
        await asyncio.gather(*pending, return_exceptions=True)


async def test_callback_subscriber_receives_event() -> None:
    broadcaster = EventBroadcaster()
    received: list[BaseModel] = []

    async def cb(event: BaseModel) -> None:
        received.append(event)

    subscriber = CallbackEventSubscriber.from_callback(cb)
    broadcaster.register(subscriber=subscriber)

    event = _DummyEvent(data=_DummyData(value=42))
    await broadcaster.publish(event=event)
    await _drain(broadcaster)

    assert len(received) == 1
    assert isinstance(received[0], _DummyEvent)
    assert received[0].data.value == 42


async def test_multiple_subscribers_all_receive() -> None:
    broadcaster = EventBroadcaster()
    counters = {"a": 0, "b": 0}

    async def cb_a(event: BaseModel) -> None:
        counters["a"] += 1

    async def cb_b(event: BaseModel) -> None:
        counters["b"] += 1

    sub_a = CallbackEventSubscriber.from_callback(cb_a)
    sub_b = CallbackEventSubscriber.from_callback(cb_b)
    broadcaster.register(subscriber=sub_a)
    broadcaster.register(subscriber=sub_b)

    await broadcaster.publish(event=_DummyEvent(data=_DummyData(value=1)))
    await _drain(broadcaster)

    assert counters == {"a": 1, "b": 1}


async def test_unregister_stops_delivery() -> None:
    broadcaster = EventBroadcaster()
    received: list[BaseModel] = []

    async def cb(event: BaseModel) -> None:
        received.append(event)

    sub = CallbackEventSubscriber.from_callback(cb)
    broadcaster.register(subscriber=sub)
    broadcaster.unregister(subscriber=sub)

    await broadcaster.publish(event=_DummyEvent(data=_DummyData(value=1)))

    assert received == []


async def test_publish_does_not_block_on_slow_subscriber() -> None:
    """A slow subscriber must not delay publish() for other subscribers
    or the publisher. publish() needs to return quickly even when one
    subscriber's callback takes seconds — otherwise the parser stalls
    on every new vacancy while AutoApply runs the AI pipeline.
    """
    broadcaster = EventBroadcaster()
    fast_received = asyncio.Event()
    slow_started = asyncio.Event()

    async def slow_cb(event: BaseModel) -> None:
        slow_started.set()
        await asyncio.sleep(0.5)

    async def fast_cb(event: BaseModel) -> None:
        fast_received.set()

    broadcaster.register(subscriber=CallbackEventSubscriber.from_callback(slow_cb))
    broadcaster.register(subscriber=CallbackEventSubscriber.from_callback(fast_cb))

    start = asyncio.get_event_loop().time()
    await broadcaster.publish(event=_DummyEvent(data=_DummyData(value=1)))
    elapsed = asyncio.get_event_loop().time() - start

    assert (
        elapsed < 0.2
    ), f"publish() took {elapsed:.2f}s — subscribers must be fire-and-forget"
    # Slow callback is still running; we only require the fast one ran promptly.
    await asyncio.wait_for(fast_received.wait(), timeout=0.2)
    assert fast_received.is_set()


async def test_publish_continues_when_subscriber_raises() -> None:
    """If one subscriber raises, others must still receive the event."""
    broadcaster = EventBroadcaster()
    other_received: list[BaseModel] = []

    async def broken_cb(event: BaseModel) -> None:
        raise RuntimeError("boom")

    async def ok_cb(event: BaseModel) -> None:
        other_received.append(event)

    broken_sub = CallbackEventSubscriber.from_callback(broken_cb)
    ok_sub = CallbackEventSubscriber.from_callback(ok_cb)
    broadcaster.register(subscriber=broken_sub)
    broadcaster.register(subscriber=ok_sub)

    await broadcaster.publish(event=_DummyEvent(data=_DummyData(value=1)))
    await _drain(broadcaster)

    assert len(other_received) == 1


async def test_publish_requires_type_field() -> None:
    class NoType(BaseModel):
        data: _DummyData

    broadcaster = EventBroadcaster()
    with pytest.raises(ValueError, match="type"):
        await broadcaster.publish(event=NoType(data=_DummyData(value=1)))


async def test_publish_requires_data_field() -> None:
    class NoData(BaseModel):
        type: Literal["x"] = "x"

    broadcaster = EventBroadcaster()
    with pytest.raises(ValueError, match="data"):
        await broadcaster.publish(event=NoData())
