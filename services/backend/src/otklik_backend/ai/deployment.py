from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel, Field, SecretStr

from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX


class LLMDeployment(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    model: str
    api_base: str | None = None
    has_api_key: bool = False

    def is_usable(self) -> bool:
        return (
            bool(self.api_base)
            or self.has_api_key
            or self.model.startswith(CLAUDE_CODE_PREFIX)
        )

    def matches(self, other: "LLMDeployment") -> bool:
        return self.model == other.model and self.api_base == other.api_base


@dataclass(frozen=True)
class ResolvedDeployment:
    deployment: LLMDeployment
    api_key: SecretStr | None = None
