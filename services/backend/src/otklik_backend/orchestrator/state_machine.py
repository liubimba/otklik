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
    # Async regeneration: any non-terminal state → LETTER_PENDING. Handed
    # off to LetterPendingWorker via the ApplicationWSEvent it publishes.
    # Distinct from LETTER_GENERATED (synchronous "letter arrived") and
    # RETRY (legacy ERROR-only arc kept for the /retry endpoint).
    REGENERATE = "regenerate"


# The only two events that land an Application in ERROR with a `reason`.
# ApplicationRepository.transition consults this to stamp `error_domain`
# straight from the event that triggered the failure — the domain is known
# for certain at the source, so the frontend never has to guess it from the
# reason text (a hh.ru "verification timeout" and an LLM "timeout" both
# contain the word "timeout", so text sniffing on the frontend would
# misattribute one as the other).
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
    skip = (
        _.LETTER_READY.to(_.SKIPPED)
        | _.LETTER_REVIEWING.to(_.SKIPPED)
        | _.ERROR.to(_.SKIPPED)
    )
    submission_ok = _.LETTER_SENDING.to(_.LETTER_SENT)
    submission_failed = _.LETTER_SENDING.to(_.ERROR)
    retry = _.ERROR.to(_.LETTER_PENDING)
    # `regenerate` is the async /application/generate entry point:
    # transitions any non-terminal, non-in-flight state to
    # LETTER_PENDING. LetterPendingWorker owns the LLM call from that
    # point on, so the /generate endpoint can return immediately and
    # the UI sees a durable LETTER_PENDING (spinner) instead of the
    # transient one that the old sync-in-handler flow produced.
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
