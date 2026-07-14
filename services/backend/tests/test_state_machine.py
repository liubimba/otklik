"""Unit tests for the Application ProcessingStateMachine.

Focused on transition legality — the higher-level api tests exercise the
same events through the HTTP surface. These tests catch state-machine
edits (adding/removing a transition arc) at the source.
"""

import pytest
from statemachine.exceptions import TransitionNotAllowed

from otklik_backend.api.schemas import ErrorDomain, ProcessingState
from otklik_backend.orchestrator.state_machine import (
    ERROR_DOMAIN_BY_EVENT,
    ApplicationEvent,
    ProcessingStateMachine,
)

# The domain each failure event is *supposed* to carry. Kept separate from
# (and checked against) ERROR_DOMAIN_BY_EVENT in state_machine.py: a pure
# key-coverage check would stay green even if FAIL and SUBMISSION_FAILED
# were swapped (ERROR_DOMAIN_BY_EVENT[SUBMISSION_FAILED] = ErrorDomain.MODEL)
# — exactly the misattribution bug this mapping exists to prevent (see the
# docstring below). Extending this dict is deliberately required in lockstep
# with ERROR_DOMAIN_BY_EVENT: the completeness assertions below fail loudly
# if either one is missing an entry the other has.
EXPECTED_ERROR_DOMAIN_BY_EVENT: dict[ApplicationEvent, ErrorDomain] = {
    ApplicationEvent.FAIL: ErrorDomain.MODEL,
    ApplicationEvent.SUBMISSION_FAILED: ErrorDomain.SUBMISSION,
}


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


def test_letter_generated_from_error_moves_to_letter_ready() -> None:
    """Regression: POST /application/generate against an ERROR-state app
    crashed with 500 because `letter_generated` did not include ERROR as
    a source state. The UI-driven "Сгенерировать заново" button now has
    a synchronous path — the RETRY path stays available for the worker
    queue variant."""
    sm = _at(ProcessingState.ERROR)
    sm.send(ApplicationEvent.LETTER_GENERATED.value)
    assert sm.current_state_value == ProcessingState.LETTER_READY


@pytest.mark.parametrize(
    "state, expected",
    [
        (ProcessingState.LETTER_PENDING, ProcessingState.LETTER_READY),
        (ProcessingState.LETTER_READY, ProcessingState.LETTER_READY),
        (ProcessingState.LETTER_REVIEWING, ProcessingState.LETTER_REVIEWING),
        (ProcessingState.ERROR, ProcessingState.LETTER_READY),
    ],
)
def test_letter_generated_arcs(
    state: ProcessingState, expected: ProcessingState
) -> None:
    """Documents every source state from which `letter_generated` succeeds."""
    sm = _at(state)
    sm.send(ApplicationEvent.LETTER_GENERATED.value)
    assert sm.current_state_value == expected


@pytest.mark.parametrize(
    "state",
    [
        ProcessingState.PARSED,
        ProcessingState.LETTER_SENDING,
        ProcessingState.LETTER_SENT,
        ProcessingState.SKIPPED,
    ],
)
def test_letter_generated_forbidden_from_terminal_or_pre_pending_states(
    state: ProcessingState,
) -> None:
    """Anything that isn't yet 'letter-authoring' (PARSED) or has already
    moved past authoring (SENDING/SENT/SKIPPED) must reject LETTER_GENERATED."""
    sm = _at(state)
    with pytest.raises(TransitionNotAllowed):
        sm.send(ApplicationEvent.LETTER_GENERATED.value)


def test_error_domain_mapping_covers_all_failure_events() -> None:
    """Dynamically discovers every event that leads to ERROR and verifies
    that ERROR_DOMAIN_BY_EVENT has an entry for each one. This ensures that
    if a new failure path is ever added, the mapping must be updated —
    avoiding silent loss of error_domain assignment. A dead domain on a
    real model error would let the UI show "verification timeout" (hh.ru)
    as if it were a model failure (CRITICAL regression from Task 12).

    ApplicationRepository.transition stamps `error_domain` from this mapping
    so the frontend never has to guess the domain from the reason text."""
    # Discover all events that lead to ERROR by brute-force testing
    # all (event, state) pairs — then verify the mapping is complete.
    events_leading_to_error = set()
    for event in ApplicationEvent:
        for state in ProcessingState:
            try:
                sm = ProcessingStateMachine(start_value=state.value)
                sm.send(event.value)
                if sm.current_state_value == ProcessingState.ERROR:
                    events_leading_to_error.add(event)
            except Exception:
                # TransitionNotAllowed is expected for most (state, event) pairs
                pass

    # ERROR_DOMAIN_BY_EVENT must have an entry for every event that reaches ERROR
    assert (
        events_leading_to_error
    ), "No events found leading to ERROR (test setup issue)"
    for event in events_leading_to_error:
        assert (
            event in ERROR_DOMAIN_BY_EVENT
        ), f"Event {event} leads to ERROR but has no entry in ERROR_DOMAIN_BY_EVENT"
        assert event in EXPECTED_ERROR_DOMAIN_BY_EVENT, (
            f"Event {event} leads to ERROR but this test has no expected domain "
            "for it — add one to EXPECTED_ERROR_DOMAIN_BY_EVENT"
        )
        # The actual regression this mapping guards against: not a missing
        # key, but a wrong value (domains swapped between two failure events).
        assert ERROR_DOMAIN_BY_EVENT[event] == EXPECTED_ERROR_DOMAIN_BY_EVENT[event], (
            f"Event {event} is mapped to {ERROR_DOMAIN_BY_EVENT[event]}, "
            f"expected {EXPECTED_ERROR_DOMAIN_BY_EVENT[event]}"
        )

    # Also verify the reverse: no stale mappings for events that don't lead to ERROR
    for event in ERROR_DOMAIN_BY_EVENT:
        assert (
            event in events_leading_to_error
        ), f"Event {event} is in ERROR_DOMAIN_BY_EVENT but doesn't lead to ERROR"
