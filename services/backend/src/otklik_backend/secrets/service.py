from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import SecretStr

from otklik_backend.ai.deployment import LLMDeployment, ResolvedDeployment
from otklik_backend.api.schemas import LLMDeploymentWriteAPISchema
from otklik_backend.secrets.store import SecretStore, account_for


@dataclass(frozen=True)
class SecretPlan:
    to_set: dict[str, str] = field(default_factory=dict)
    to_delete: list[str] = field(default_factory=list)


class DeploymentSecretsService:
    def __init__(self, store: SecretStore) -> None:
        self._store = store

    def plan(
        self,
        current: list[LLMDeployment],
        incoming: list[LLMDeploymentWriteAPISchema],
    ) -> tuple[list[LLMDeployment], SecretPlan]:
        by_id = {d.id: d for d in current}
        deployments: list[LLMDeployment] = []
        to_set: dict[str, str] = {}
        to_delete: list[str] = []
        kept_ids: set[str] = set()

        for item in incoming:
            existing = by_id.pop(item.id, None) if item.id else None
            deployment_id = existing.id if existing else uuid4().hex
            kept_ids.add(deployment_id)
            has_key = existing.has_api_key if existing else False
            if item.api_key is None:
                pass
            elif item.api_key == "":
                has_key = False
                to_delete.append(account_for(deployment_id))
            else:
                has_key = True
                to_set[account_for(deployment_id)] = item.api_key
            deployments.append(
                LLMDeployment(
                    id=deployment_id,
                    model=item.model,
                    api_base=item.api_base,
                    has_api_key=has_key,
                )
            )

        for deployment in current:
            if deployment.id not in kept_ids and deployment.has_api_key:
                to_delete.append(account_for(deployment.id))

        return deployments, SecretPlan(to_set=to_set, to_delete=to_delete)

    async def commit(self, plan: SecretPlan) -> None:
        for account, secret in plan.to_set.items():
            await self._store.set(account, secret)
        for account in plan.to_delete:
            await self._store.delete(account)

    async def resolve(
        self, deployments: list[LLMDeployment]
    ) -> list[ResolvedDeployment]:
        resolved: list[ResolvedDeployment] = []
        for deployment in deployments:
            secret: str | None = None
            if deployment.has_api_key:
                secret = await self._store.get(account_for(deployment.id))
            resolved.append(
                ResolvedDeployment(
                    deployment=deployment,
                    api_key=SecretStr(secret) if secret else None,
                )
            )
        return resolved
