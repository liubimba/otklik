from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel, Field, SecretStr, model_validator

from otklik_backend.setup.constants import CLAUDE_CODE_PREFIX


class LLMDeployment(BaseModel):
    # Явный устойчивый id: он же имя аккаунта в хранилище ключей. Раньше
    # идентичность считалась хешем от полей ВМЕСТЕ С ключом — из-за этого ротация
    # ключа порождала дубль вместо замены, а хранилищу было не за что зацепиться.
    id: str = Field(default_factory=lambda: uuid4().hex)
    model: str
    # ВРЕМЕННО: ключ ещё живёт в БД. Удаляется в задаче 5, когда ключи переедут
    # в хранилище окончательно. exclude=True: с задачи 3 ключ больше никогда
    # не попадает ни в один response — ни здесь, ни через SettingsRepository
    # (после задачи 3 сюда пишется только None, см. DeploymentSecretsService.plan).
    api_key: str | None = Field(default=None, exclude=True)
    api_base: str | None = None
    has_api_key: bool = False

    @model_validator(mode="after")
    def _sync_has_api_key(self) -> "LLMDeployment":
        """ВРЕМЕННО (пока api_key ещё живёт в БД, до задачи 5): запись,
        прочитанная из БД с непустым api_key, но без has_api_key (старые
        строки, ручные конструкторы), не должна регрессировать в
        is_usable() == False. Умирает вместе с api_key."""
        if self.api_key and not self.has_api_key:
            self.has_api_key = True
        return self

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

    def resolve(self) -> "ResolvedDeployment":
        """ВРЕМЕННЫЙ шим на время переезда: ключ пока лежит здесь же. В задаче 5
        исчезает вместе с полем api_key — тогда ключи выдаёт только хранилище."""
        return ResolvedDeployment(
            deployment=self,
            api_key=SecretStr(self.api_key) if self.api_key else None,
        )


@dataclass(frozen=True)
class ResolvedDeployment:
    """Runtime-only: deployment плюс ключ, вынутый из хранилища. Живёт от
    SecretStore до Router'а.

    Намеренно НЕ pydantic: у этого типа нет model_dump(), поэтому «случайно
    сериализовать ключ наружу» им физически нечем. SecretStr сверху закрывает
    репры и логи."""

    deployment: LLMDeployment
    api_key: SecretStr | None = None
