# SubmissionResult / SubmissionResultType are the canonical domain result of
# a per-site submit attempt. The current implementation still lives under
# browser.writer.SubmitResult / SubmitResultType — this module re-exports
# them as SubmissionResult / SubmissionResultType so downstream code depends
# on the domain-level names, not on browser/. The physical move to
# core/site/result.py as the source-of-truth happens in stage 5.2.
from headhunter_backend.browser.writer import (
    SubmitResult as SubmissionResult,
    SubmitResultType as SubmissionResultType,
)

__all__ = ["SubmissionResult", "SubmissionResultType"]
