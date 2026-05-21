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


class WorkFormat(str, Enum):
    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    TRAVELING = "traveling"
    UNKNOWN = "unknown"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"  # Полная занятость
    ROTATIONAL = "rotational"  # Вахта
    PART_TIME = "part_time"  # Частичная занятость
    SIDE_JOB = "side_job"  # Подработка
    CONTRACT = "contract"  # Оформление по ГПХ или по совместительству
    INTERNSHIP = "internship"  # Стажировка
    UNKNOWN = "unknown"
