from pydantic import BaseModel
import hashlib


class LLMDeployment(BaseModel):
    model: str
    api_key: str | None = None
    api_base: str | None = None

    def id(self) -> str:
        raw = f"{self.model}#{self.api_key or ''}#{self.api_base or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
