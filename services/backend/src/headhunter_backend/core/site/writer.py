from typing import Protocol, runtime_checkable

from headhunter_backend.core.site.result import SubmissionResult
from headhunter_backend.core.site.selectors import SiteSelectors


@runtime_checkable
class SiteWriter(Protocol):
    async def submit(
        self,
        vacancy_url: str,
        letter_text: str,
        selectors: SiteSelectors,
    ) -> SubmissionResult: ...
