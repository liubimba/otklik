from pydantic import BaseModel
import hashlib

from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX


class LLMDeployment(BaseModel):
    model: str
    api_key: str | None = None
    api_base: str | None = None

    def id(self) -> str:
        raw = f"{self.model}#{self.api_key or ''}#{self.api_base or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_usable(self) -> bool:
        """Deployment, которым можно реально пользоваться, а не просто
        занимает место в списке.

        Локальная модель (у неё задан `api_base` — адрес Ollama) ключа не
        просит. Облачная (без `api_base`) без ключа гарантированно упадёт
        на первом же запросе. Claude Code (`claude-code/...`) не имеет ни
        `api_base`, ни `api_key` — auth живёт в CLI/подписке, но он рабочий."""
        return (
            bool(self.api_base)
            or bool(self.api_key)
            or self.model.startswith(CLAUDE_CODE_PREFIX)
        )
