"""Таблица истинности DeploymentSecretsService.plan() — чистая функция, без
хранилища, БД и HTTP. Единственное место, где живёт правило
«None — не трогаем, "" — удаляем, иначе пишем»."""

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.api.schemas import LLMDeploymentWriteAPISchema
from otklik_backend.secrets.service import DeploymentSecretsService
from otklik_backend.secrets.store import account_for


def make_service() -> DeploymentSecretsService:
    # store не нужен — plan() его не трогает.
    return DeploymentSecretsService(store=None)  # type: ignore[arg-type]


def test_absent_api_key_keeps_the_stored_key_and_has_api_key() -> None:
    existing = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    incoming = LLMDeploymentWriteAPISchema(
        id=existing.id, model="gigachat/GigaChat-2"
    )  # api_key отсутствует

    deployments, plan = make_service().plan(current=[existing], incoming=[incoming])

    assert deployments[0].id == existing.id
    assert deployments[0].has_api_key is True
    assert plan.to_set == {}
    assert plan.to_delete == []


def test_none_api_key_keeps_the_stored_key_and_has_api_key() -> None:
    """Явный null в JSON ведёт себя так же, как отсутствующее поле."""
    existing = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    incoming = LLMDeploymentWriteAPISchema(
        id=existing.id, model="gigachat/GigaChat-2", api_key=None
    )

    deployments, plan = make_service().plan(current=[existing], incoming=[incoming])

    assert deployments[0].has_api_key is True
    assert plan.to_set == {}
    assert plan.to_delete == []


def test_empty_string_clears_the_key() -> None:
    existing = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    incoming = LLMDeploymentWriteAPISchema(
        id=existing.id, model="gigachat/GigaChat-2", api_key=""
    )

    deployments, plan = make_service().plan(current=[existing], incoming=[incoming])

    assert deployments[0].has_api_key is False
    assert plan.to_set == {}
    assert plan.to_delete == [account_for(existing.id)]


def test_non_empty_string_sets_the_key() -> None:
    existing = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=False)
    incoming = LLMDeploymentWriteAPISchema(
        id=existing.id, model="gigachat/GigaChat-2", api_key="sk-new"
    )

    deployments, plan = make_service().plan(current=[existing], incoming=[incoming])

    assert deployments[0].has_api_key is True
    assert plan.to_set == {account_for(existing.id): "sk-new"}
    assert plan.to_delete == []


def test_dropped_deployment_deletes_its_stored_key() -> None:
    kept = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    dropped = LLMDeployment(model="openai/gpt-4o", has_api_key=True)
    incoming = [LLMDeploymentWriteAPISchema(id=kept.id, model=kept.model)]

    deployments, plan = make_service().plan(current=[kept, dropped], incoming=incoming)

    assert len(deployments) == 1
    assert deployments[0].id == kept.id
    assert plan.to_delete == [account_for(dropped.id)]


def test_dropped_deployment_without_a_key_produces_no_delete() -> None:
    """Удалять из хранилища нечего — не плодим шум в плане."""
    kept = LLMDeployment(model="gigachat/GigaChat-2", has_api_key=True)
    dropped = LLMDeployment(model="openai/gpt-4o", has_api_key=False)
    incoming = [LLMDeploymentWriteAPISchema(id=kept.id, model=kept.model)]

    _, plan = make_service().plan(current=[kept, dropped], incoming=incoming)

    assert plan.to_delete == []


def test_absent_id_mints_a_fresh_server_side_id() -> None:
    incoming = LLMDeploymentWriteAPISchema(model="ollama_chat/qwen2.5:7b")

    deployments, plan = make_service().plan(current=[], incoming=[incoming])

    assert deployments[0].id  # непустой
    assert deployments[0].has_api_key is False
    assert plan.to_set == {}
    assert plan.to_delete == []


def test_unknown_client_supplied_id_is_not_trusted() -> None:
    """id, которого нет в current, не может стать именем аккаунта — иначе
    любая веб-страница (CORS сейчас открыт всем) могла бы подсунуть id и
    перезаписать чужой секрет по предсказуемому имени аккаунта."""
    incoming = LLMDeploymentWriteAPISchema(
        id="attacker-supplied-id", model="ollama_chat/qwen2.5:7b", api_key="sk-x"
    )

    deployments, plan = make_service().plan(current=[], incoming=[incoming])

    minted_id = deployments[0].id
    assert minted_id != "attacker-supplied-id"
    assert plan.to_set == {account_for(minted_id): "sk-x"}
    assert account_for("attacker-supplied-id") not in plan.to_set
