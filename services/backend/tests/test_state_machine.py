"""Unit tests for the Application ProcessingStateMachine.

Focused on transition legality — the higher-level api tests exercise the
same events through the HTTP surface. These tests catch state-machine
edits (adding/removing a transition arc) at the source.
"""

import pytest
from statemachine.exceptions import TransitionNotAllowed

from headhunter_backend.api.schemas import ProcessingState
from headhunter_backend.orchestrator.state_machine import (
    ApplicationEvent,
    ProcessingStateMachine,
)


def _at(state: ProcessingState) -> ProcessingStateMachine:
    """Instantiate the state machine already parked in a specific state.

    The library exposes each state as a class-level attribute keyed by name,
    so we look up the target state on the machine and pass it as the initial
    state through the constructor.
    """
    sm = ProcessingStateMachine(start_value=state.value)
    assert sm.current_state_value == state
    return sm


def test_submit_from_letter_ready_moves_to_letter_sending() -> None:
    sm = _at(ProcessingState.LETTER_READY)
    sm.send(ApplicationEvent.SUBMIT.value)
    assert sm.current_state_value == ProcessingState.LETTER_SENDING


def test_submit_from_letter_reviewing_moves_to_letter_sending() -> None:
    sm = _at(ProcessingState.LETTER_REVIEWING)
    sm.send(ApplicationEvent.SUBMIT.value)
    assert sm.current_state_value == ProcessingState.LETTER_SENDING


def test_submit_from_error_moves_to_letter_sending() -> None:
    """Regression: prior to the ERROR arc, a failed submit could only be
    recovered via RETRY (which regenerates via the LLM). This transition
    lets the user re-submit an existing letter after a transient failure
    without losing manual edits."""
    sm = _at(ProcessingState.ERROR)
    sm.send(ApplicationEvent.SUBMIT.value)
    assert sm.current_state_value == ProcessingState.LETTER_SENDING


@pytest.mark.parametrize(
    "state",
    [
        ProcessingState.PARSED,
        ProcessingState.LETTER_PENDING,
        ProcessingState.LETTER_SENDING,
        ProcessingState.LETTER_SENT,
        ProcessingState.SKIPPED,
    ],
)
def test_submit_forbidden_from_non_authoring_states(
    state: ProcessingState,
) -> None:
    sm = _at(state)
    with pytest.raises(TransitionNotAllowed):
        sm.send(ApplicationEvent.SUBMIT.value)


def test_retry_from_error_moves_to_letter_pending() -> None:
    """Retry stays as-is — regenerates the letter via the worker."""
    sm = _at(ProcessingState.ERROR)
    sm.send(ApplicationEvent.RETRY.value)
    assert sm.current_state_value == ProcessingState.LETTER_PENDING


def test_error_state_offers_both_submit_and_retry_paths() -> None:
    """Documents the two distinct forward paths out of ERROR — SUBMIT
    when the user has a usable letter and just wants to retry sending,
    RETRY when they want a fresh LLM regeneration."""
    for event, expected in (
        (ApplicationEvent.SUBMIT, ProcessingState.LETTER_SENDING),
        (ApplicationEvent.RETRY, ProcessingState.LETTER_PENDING),
    ):
        sm = _at(ProcessingState.ERROR)
        sm.send(event.value)
        assert sm.current_state_value == expected
