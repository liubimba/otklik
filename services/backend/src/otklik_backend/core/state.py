from enum import Enum


class ProcessingState(str, Enum):
    PARSED = "parsed"
    LETTER_PENDING = "letter_pending"
    LETTER_READY = "letter_ready"
    LETTER_REVIEWING = "letter_reviewing"
    LETTER_SENDING = "letter_sending"
    LETTER_SENT = "letter_sent"
    ERROR = "error"
    SKIPPED = "skipped"


class ErrorDomain(str, Enum):
    """Which subsystem produced the ERROR-state `reason`.

    Set at the transition that lands an Application in ERROR (see
    `orchestrator.state_machine.ERROR_DOMAIN_BY_EVENT`), never guessed
    from the reason text on the frontend — MODEL and SUBMISSION reasons
    can both contain words like "timeout", so text sniffing would
    misattribute a hh.ru submission failure to the LLM (or vice versa).
    """

    MODEL = "model"
    SUBMISSION = "submission"
