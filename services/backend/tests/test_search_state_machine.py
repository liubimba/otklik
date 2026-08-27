from otklik_backend.api.schemas import SearchStatusAPISchema
from otklik_backend.orchestrator.search.search_session import (
    SearchStateEvent,
    SearchStatusStateMachine,
)


def _running() -> SearchStatusStateMachine:
    sm = SearchStatusStateMachine()
    sm.send(SearchStateEvent.RUN.value)
    return sm


def test_running_search_can_pause_and_resume() -> None:
    sm = _running()

    sm.send(SearchStateEvent.PAUSE.value)
    assert sm.current_state_value == SearchStatusAPISchema.PAUSED
    assert not sm.is_terminated

    sm.send(SearchStateEvent.RESUME.value)
    assert sm.current_state_value == SearchStatusAPISchema.RUNNING


def test_paused_search_can_be_cancelled() -> None:
    sm = _running()
    sm.send(SearchStateEvent.PAUSE.value)

    sm.send(SearchStateEvent.CANCELED.value)
    assert sm.current_state_value == SearchStatusAPISchema.CANCELED
    assert sm.is_terminated


def test_paused_is_still_an_active_status() -> None:
    assert SearchStatusAPISchema.PAUSED.is_active()
