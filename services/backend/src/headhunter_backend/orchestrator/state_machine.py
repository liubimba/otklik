from statemachine import StateMachine
from statemachine.states import States
from headhunter_backend.api.schemas import ProcessingState
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
        # ERROR → LETTER_READY: mirrors the SUBMIT arc for the "regenerate"
        # button in the error-state footer. The user explicitly asked the
        # LLM for a fresh letter — deliver it. The RETRY path also lands
        # in LETTER_READY (via LETTER_PENDING + worker), but goes through
        # the queue; this arc is the synchronous UI-driven variant.
        | _.ERROR.to(_.LETTER_READY)
    )
    send_for_review = _.LETTER_READY.to(_.LETTER_REVIEWING)
    submit = (
        _.LETTER_READY.to(_.LETTER_SENDING)
        | _.LETTER_REVIEWING.to(_.LETTER_SENDING)
        # ERROR → LETTER_SENDING lets the user re-submit after a failed
        # send without going through RETRY (which regenerates the letter
        # via the LLM and clobbers any manual edits). Pairs with the UI
        # "Отправить" button in the error-state footer.
        | _.ERROR.to(_.LETTER_SENDING)
    )
    skip = _.LETTER_REVIEWING.to(_.SKIPPED)
    submission_ok = _.LETTER_SENDING.to(_.LETTER_SENT)
    submission_failed = _.LETTER_SENDING.to(_.ERROR)
    retry = _.ERROR.to(_.LETTER_PENDING)
    fail = (
        _.LETTER_PENDING.to(_.ERROR)
        | _.LETTER_READY.to(_.ERROR)
        | _.LETTER_REVIEWING.to(_.ERROR)
    )
