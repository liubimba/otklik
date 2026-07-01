from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.browser.core import BrowserCore
from headhunter_backend.db.repositories.rate_limits import (
    RateLimitExceeded,
    RateLimitRepository,
)


class GateResult(str, Enum):
    PROCEED = "proceed"
    NOT_AUTHORIZED = "not_authorized"
    RATE_LIMITED = "rate_limited"


async def auth_gate(browser: BrowserCore) -> GateResult:
    auth_status = await browser.get_auth_status()
    if not auth_status.is_authorized():
        return GateResult.NOT_AUTHORIZED
    return GateResult.PROCEED


async def rate_limit_gate(session: AsyncSession) -> GateResult:
    try:
        await RateLimitRepository.ensure_within_limits(session=session)
    except RateLimitExceeded:
        return GateResult.RATE_LIMITED
    return GateResult.PROCEED
