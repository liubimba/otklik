from enum import Enum


class ProcessingState(str, Enum):
    PARSED = "parsed"
    LETTER_PENDING = "letter_pending"
    LETTER_READY = "letter_ready"
    LETTER_REVIEWING = "letter_reviewing"
    LETTER_QUEUED = "letter_queued"
    LETTER_SENDING = "letter_sending"
    LETTER_SENT = "letter_sent"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    ALREADY_APPLIED = "already_applied"
    SKIPPED = "skipped"


class ErrorDomain(str, Enum):
    MODEL = "model"
    SUBMISSION = "submission"
