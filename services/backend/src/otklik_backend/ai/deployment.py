from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel, Field, SecretStr

from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX


class LLMDeployment(BaseModel):
    # Явный устойчивый id: он же имя аккаунта в хранилище ключей. Раньше
    # идентичность считалась хешем от полей ВМЕСТЕ С ключом — из-за этого ротация
    # ключа порождала дубль вместо замены, а хранилищу было не за что зацепиться.
    id: str = Field(default_factory=lambda: uuid4().hex)
    model: str
    api_base: str | None = None
    has_api_key: bool = False

    def is_usable(self) -> bool:
        """Deployment, которым можно реально пользоваться, а не просто
        занимает место в списке.

        Локальная модель (задан `api_base`) ключа не просит. Облачная без ключа
        гарантированно упадёт на первом же запросе. Claude Code (`claude-code/...`)
        не имеет ни `api_base`, ни ключа — auth живёт в CLI, но он рабочий."""
        return (
            bool(self.api_base)
            or self.has_api_key
            or self.model.startswith(CLAUDE_CODE_PREFIX)
        )

    def matches(self, other: "LLMDeployment") -> bool:
        """«Тот же самый deployment» с точки зрения мастера: модель и адрес.
        Ключ и id в сравнение не входят — иначе смена ключа даёт дубль вместо
        замены (ровно этот баг и был, пока идентичность считалась от ключа)."""
        return self.model == other.model and self.api_base == other.api_base


@dataclass(frozen=True)
class ResolvedDeployment:
    """Runtime-only: deployment плюс ключ, вынутый из хранилища. Живёт от
    SecretStore до Router'а.

    Намеренно НЕ pydantic: у этого типа нет model_dump(), поэтому «случайно
    сериализовать ключ наружу» им физически нечем. SecretStr сверху закрывает
    репры и логи."""

    deployment: LLMDeployment
    api_key: SecretStr | None = None
