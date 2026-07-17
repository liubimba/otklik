from statemachine import StateMachine
from statemachine.states import States
from otklik_backend.api.schemas import ErrorDomain, ProcessingState
from enum import Enum


class ApplicationEvent(str, Enum):
    ENQUEUE_FOR_LETTER = "enqueue_for_letter"
    LETTER_GENERATED = "letter_generated"
    SEND_FOR_REVIEW = "send_for_review"
    SUBMIT = "submit"
    SKIP = "skip"
    SUBMISSION_OK = "submission_ok"
    SUBMISSION_FAILED = "submission_failed"
    RETRY = "retry"
    FAIL = "fail"
    REGENERATE = "regenerate"


ERROR_DOMAIN_BY_EVENT: dict[ApplicationEvent, ErrorDomain] = {
    ApplicationEvent.FAIL: ErrorDomain.MODEL,
    ApplicationEvent.SUBMISSION_FAILED: ErrorDomain.SUBMISSION,
}


class ProcessingStateMachine(StateMachine):
    _ = States.from_enum(
        ProcessingState,
        initial=ProcessingState.PARSED,
        final=[ProcessingState.LETTER_SENT, ProcessingState.SKIPPED],
    )

    enqueue_for_letter = _.PARSED.to(_.LETTER_PENDING)
    letter_generated = (
        _.LETTER_PENDING.to(_.LETTER_READY)
        | _.LETTER_READY.to(_.LETTER_READY)
        | _.LETTER_REVIEWING.to(_.LETTER_REVIEWING)
        | _.ERROR.to(_.LETTER_READY)
    )
    send_for_review = _.LETTER_READY.to(_.LETTER_REVIEWING)
    submit = (
        _.LETTER_READY.to(_.LETTER_SENDING)
        | _.LETTER_REVIEWING.to(_.LETTER_SENDING)
        | _.ERROR.to(_.LETTER_SENDING)
    )
    skip = (
        _.LETTER_READY.to(_.SKIPPED)
        | _.LETTER_REVIEWING.to(_.SKIPPED)
        | _.ERROR.to(_.SKIPPED)
    )
    submission_ok = _.LETTER_SENDING.to(_.LETTER_SENT)
    submission_failed = _.LETTER_SENDING.to(_.ERROR)
    retry = _.ERROR.to(_.LETTER_PENDING)
    regenerate = (
        _.PARSED.to(_.LETTER_PENDING)
        | _.LETTER_READY.to(_.LETTER_PENDING)
        | _.LETTER_REVIEWING.to(_.LETTER_PENDING)
        | _.ERROR.to(_.LETTER_PENDING)
    )
    fail = (
        _.LETTER_PENDING.to(_.ERROR)
        | _.LETTER_READY.to(_.ERROR)
        | _.LETTER_REVIEWING.to(_.ERROR)
    )
