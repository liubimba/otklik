import pytest
from statemachine.exceptions import TransitionNotAllowed

from otklik_backend.api.schemas import ErrorDomain, ProcessingState
from otklik_backend.orchestrator.state_machine import (
    ERROR_DOMAIN_BY_EVENT,
    ApplicationEvent,
    ProcessingStateMachine,
)

EXPECTED_ERROR_DOMAIN_BY_EVENT: dict[ApplicationEvent, ErrorDomain] = {
    ApplicationEvent.FAIL: ErrorDomain.MODEL,
    ApplicationEvent.SUBMISSION_FAILED: ErrorDomain.SUBMISSION,
}


def _at(state: ProcessingState) -> ProcessingStateMachine:
    sm = ProcessingStateMachine(start_value=state.value)
    assert sm.current_state_value == state
    return sm


def _skip_succeeds_from(state: ProcessingState) -> bool:
    sm = _at(state)
    try:
        sm.send(ApplicationEvent.SKIP.value)
    except TransitionNotAllowed:
        return False
    return True


def test_submit_from_letter_ready_moves_to_letter_sending() -> None:
    sm = _at(ProcessingState.LETTER_READY)
    sm.send(ApplicationEvent.SUBMIT.value)
    assert sm.current_state_value == ProcessingState.LETTER_SENDING


def test_submit_from_letter_reviewing_moves_to_letter_sending() -> None:
    sm = _at(ProcessingState.LETTER_REVIEWING)
    sm.send(ApplicationEvent.SUBMIT.value)
    assert sm.current_state_value == ProcessingState.LETTER_SENDING


def test_submit_from_error_moves_to_letter_sending() -> None:
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


def test_skip_from_error_moves_to_skipped() -> None:
    sm = _at(ProcessingState.ERROR)
    sm.send(ApplicationEvent.SKIP.value)
    assert sm.current_state_value == ProcessingState.SKIPPED


def test_skip_from_letter_ready_moves_to_skipped() -> None:
    sm = _at(ProcessingState.LETTER_READY)
    sm.send(ApplicationEvent.SKIP.value)
    assert sm.current_state_value == ProcessingState.SKIPPED


def test_skip_from_letter_reviewing_moves_to_skipped() -> None:
    sm = _at(ProcessingState.LETTER_REVIEWING)
    sm.send(ApplicationEvent.SKIP.value)
    assert sm.current_state_value == ProcessingState.SKIPPED


SKIP_SOURCE_STATES_OFFERED_BY_THE_SHEET_FOOTER = [
    ProcessingState.LETTER_READY,
    ProcessingState.LETTER_REVIEWING,
    ProcessingState.ERROR,
]


def test_skip_arcs_match_exactly_the_states_the_sheet_footer_offers() -> None:
    allowed = [state for state in ProcessingState if _skip_succeeds_from(state)]
    assert allowed == SKIP_SOURCE_STATES_OFFERED_BY_THE_SHEET_FOOTER


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
def test_skip_forbidden_from_states_the_sheet_footer_does_not_offer(
    state: ProcessingState,
) -> None:
    sm = _at(state)
    with pytest.raises(TransitionNotAllowed):
        sm.send(ApplicationEvent.SKIP.value)


def test_retry_from_error_moves_to_letter_pending() -> None:
    sm = _at(ProcessingState.ERROR)
    sm.send(ApplicationEvent.RETRY.value)
    assert sm.current_state_value == ProcessingState.LETTER_PENDING


def test_error_state_offers_both_submit_and_retry_paths() -> None:
    for event, expected in (
        (ApplicationEvent.SUBMIT, ProcessingState.LETTER_SENDING),
        (ApplicationEvent.RETRY, ProcessingState.LETTER_PENDING),
    ):
        sm = _at(ProcessingState.ERROR)
        sm.send(event.value)
        assert sm.current_state_value == expected


def test_letter_generated_from_error_moves_to_letter_ready() -> None:
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
def test_letter_generated_succeeds_from_every_letter_authoring_state(
    state: ProcessingState, expected: ProcessingState
) -> None:
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
    sm = _at(state)
    with pytest.raises(TransitionNotAllowed):
        sm.send(ApplicationEvent.LETTER_GENERATED.value)


def test_error_domain_mapping_covers_all_failure_events() -> None:
    events_leading_to_error = set()
    for event in ApplicationEvent:
        for state in ProcessingState:
            try:
                sm = ProcessingStateMachine(start_value=state.value)
                sm.send(event.value)
                if sm.current_state_value == ProcessingState.ERROR:
                    events_leading_to_error.add(event)
            except Exception:
                pass

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
        assert ERROR_DOMAIN_BY_EVENT[event] == EXPECTED_ERROR_DOMAIN_BY_EVENT[event], (
            f"Event {event} is mapped to {ERROR_DOMAIN_BY_EVENT[event]}, "
            f"expected {EXPECTED_ERROR_DOMAIN_BY_EVENT[event]}"
        )

    for event in ERROR_DOMAIN_BY_EVENT:
        assert (
            event in events_leading_to_error
        ), f"Event {event} is in ERROR_DOMAIN_BY_EVENT but doesn't lead to ERROR"
