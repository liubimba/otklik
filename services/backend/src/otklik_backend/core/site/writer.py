from typing import Protocol, runtime_checkable

from otklik_backend.core.site.result import SubmissionResult


@runtime_checkable
class SiteWriter(Protocol):
    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult: ...
