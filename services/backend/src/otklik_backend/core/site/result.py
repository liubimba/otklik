from dataclasses import dataclass
from enum import Enum


class SubmissionResultType(str, Enum):
    CAPTCHA = "captcha"
    SUBMITTED = "submitted"
    FAILED = "failed"


@dataclass(frozen=True)
class SubmissionResult:
    type: SubmissionResultType
    reason: str | None = None

    @classmethod
    def submitted(cls) -> "SubmissionResult":
        return cls(type=SubmissionResultType.SUBMITTED)

    @classmethod
    def captcha(cls) -> "SubmissionResult":
        return cls(type=SubmissionResultType.CAPTCHA)

    @classmethod
    def failed(cls, reason: str) -> "SubmissionResult":
        return cls(type=SubmissionResultType.FAILED, reason=reason)
