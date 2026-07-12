from typing import Protocol, runtime_checkable

from otklik_backend.core.site.result import SubmissionResult


@runtime_checkable
class SiteWriter(Protocol):
    """Per-site submission writer. Selectors, delays and any per-site
    configuration live on the concrete implementation."""

    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult: ...
