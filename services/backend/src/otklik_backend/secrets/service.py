from dataclasses import dataclass, field
from uuid import uuid4

from pydantic import SecretStr

from otklik_backend.ai.deployment import LLMDeployment, ResolvedDeployment
from otklik_backend.api.schemas import LLMDeploymentWriteAPISchema
from otklik_backend.secrets.store import SecretStore, account_for


@dataclass(frozen=True)
class SecretPlan:
    """Что нужно сделать с хранилищем, чтобы оно сошлось с новым списком."""

    to_set: dict[str, str] = field(default_factory=dict)  # account -> secret
    to_delete: list[str] = field(default_factory=list)  # accounts


class DeploymentSecretsService:
    """Единственное место, где ключи входят в рантайм и уходят в хранилище.
    Всё остальное приложение ключей не видит."""

    def __init__(self, store: SecretStore) -> None:
        self._store = store

    def plan(
        self,
        current: list[LLMDeployment],
        incoming: list[LLMDeploymentWriteAPISchema],
    ) -> tuple[list[LLMDeployment], SecretPlan]:
        """Чистая функция и единственное место, где живёт правило
        «None — не трогаем, "" — удаляем, иначе пишем».

        Возвращает полный список для колонки (без ключей, с посчитанным
        has_api_key) и план для хранилища. Ничего не пишет.

        Список для колонки считается ЗДЕСЬ, а не берётся из запроса — иначе
        слепой копипаст колонок в SettingsRepository.update мог бы получить
        неполный список и стереть ключи (см. регресс-тест
        test_settings_update_unrelated_field_keeps_api_key)."""
        by_id = {d.id: d for d in current}
        deployments: list[LLMDeployment] = []
        to_set: dict[str, str] = {}
        to_delete: list[str] = []
        kept_ids: set[str] = set()

        for item in incoming:
            # Клиентскому id доверяем, только если он совпадает с существующей
            # записью: id становится именем аккаунта в хранилище, а любая
            # веб-страница сейчас может достучаться до этого эндпоинта (CORS).
            #
            # pop, а не get: каждую существующую запись можно забрать лишь один
            # раз. Иначе два входящих item'а с одним и тем же id получили бы
            # общий deployment_id — то есть общий аккаунт в хранилище: ключ
            # второго молча затёр бы ключ первого, а удаление одной строки
            # убило бы ключ другой. Второй такой item честно считается новым.
            existing = by_id.pop(item.id, None) if item.id else None
            deployment_id = existing.id if existing else uuid4().hex
            kept_ids.add(deployment_id)
            has_key = existing.has_api_key if existing else False
            if item.api_key is None:
                pass  # не трогаем: has_key остаётся как был
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

        # Deployment'ы, исчезнувшие из запроса, чистят за собой хранилище —
        # иначе оно копит сирот.
        for deployment in current:
            if deployment.id not in kept_ids and deployment.has_api_key:
                to_delete.append(account_for(deployment.id))

        return deployments, SecretPlan(to_set=to_set, to_delete=to_delete)

    async def commit(self, plan: SecretPlan) -> None:
        """Исполняет план. Сначала записи, потом удаления: при частичном сбое
        лучше оставить лишний секрет (сирота, безвредно и подметается), чем
        снести нужный."""
        for account, secret in plan.to_set.items():
            await self._store.set(account, secret)
        for account in plan.to_delete:
            await self._store.delete(account)

    async def resolve(
        self, deployments: list[LLMDeployment]
    ) -> list[ResolvedDeployment]:
        """Обратный путь: список из БД + ключи из хранилища → то, что ест AILayer.
        Единственное место, где ключ попадает в рантайм."""
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
