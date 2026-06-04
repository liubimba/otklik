from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AICoverLetterResult:
    text: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    was_fallback: bool
    cost_usd: Optional[float] = None
