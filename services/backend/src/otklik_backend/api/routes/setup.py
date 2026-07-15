import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.api.dependencies import (
    AILayerDep,
    BenchmarkRunnerDep,
    HardwareProbeDep,
    OllamaGateDep,
    SessionDep,
)
from otklik_backend.api.schemas import (
    LocalSetupStateAPISchema,
    SettingsAPISchema,
    SetupStateAPISchema,
)
from otklik_backend.db.converters import settings_to_orm, settings_to_schema
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.log import get_logger
from otklik_backend.setup.benchmark import BenchmarkResult
from otklik_backend.setup.constants import (
    CLOUD_MODEL,
    LOCAL_MODEL,
    LOCAL_MODEL_TAG,
    OLLAMA_HOST,
)
from otklik_backend.setup.ollama import OllamaPullError

log = get_logger(__name__)

setup_router = APIRouter(prefix="/setup", tags=["setup"])


@setup_router.get("/state")
async def setup_state(
    session: SessionDep, hardware: HardwareProbeDep, ollama: OllamaGateDep
) -> SetupStateAPISchema:
    settings: SettingsORM = await SettingsRepository.get(session=session)
    return SetupStateAPISchema(
        hardware=hardware.probe(),
        ollama=await ollama.state(),
        has_deployment=any(item.is_usable() for item in settings.llm_deployments),
        local_model=LOCAL_MODEL,
        cloud_model=CLOUD_MODEL,
    )


@setup_router.get("/local")
async def setup_local(ollama: OllamaGateDep) -> LocalSetupStateAPISchema:
    installed = await ollama.list_models()
    return LocalSetupStateAPISchema(
        ollama_state=await ollama.state(),
        installed_models=installed,
        recommended_tag=LOCAL_MODEL_TAG,
        recommended_installed=LOCAL_MODEL_TAG in installed,
    )


@setup_router.post("/pull")
async def setup_pull(ollama: OllamaGateDep) -> StreamingResponse:
    """Стримит прогресс загрузки модели кадрами SSE — тем же форматом, что и
    чат письма, поэтому фронтенд читает его уже готовым парсером.

    Ответ коммитится со статусом 200 в момент первого кадра, поэтому упавшую
    на середине загрузку (нет места, нет сети, битый ответ Ollama) нельзя
    доставить HTTP-статусом — соединение к тому моменту уже открыто.
    Доставляем такую ошибку отдельным кадром `error` внутри того же стрима,
    после чего закрываем его штатно, чтобы полоса прогресса на фронтенде не
    висела вечно.
    """

    async def frames() -> AsyncIterator[str]:
        try:
            async for progress in ollama.pull():
                yield f"data: {progress.model_dump_json()}\n\n"
        except OllamaPullError as exc:
            log.warning("Model pull failed", detail=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            log.error("Model pull failed unexpectedly", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Model pull failed'})}\n\n"

    return StreamingResponse(frames(), media_type="text/event-stream")


@setup_router.post("/benchmark")
async def setup_benchmark(runner: BenchmarkRunnerDep) -> BenchmarkResult:
    return await runner.run(
        deployment=LLMDeployment(model=LOCAL_MODEL, api_base=OLLAMA_HOST)
    )


@setup_router.post("/deployment")
async def setup_deployment(
    session: SessionDep, ai_layer: AILayerDep, deployment: LLMDeployment
) -> SettingsAPISchema:
    """Записывает deployment в настройки. Идемпотентно: повторное прохождение
    шага не плодит дублей (сверка по LLMDeployment.id(), который хеширует
    model+key+base)."""
    settings: SettingsAPISchema = settings_to_schema(
        orm=await SettingsRepository.get(session=session)
    )
    existing_ids = {item.id() for item in settings.llm.deployments}
    if deployment.id() not in existing_ids:
        settings.llm.deployments = [*settings.llm.deployments, deployment]
        updated: SettingsORM = await SettingsRepository.update(
            session=session, new_settings=settings_to_orm(settings)
        )
        ai_layer.rebuild(deployments=updated.llm_deployments)
        return settings_to_schema(orm=updated)
    return settings
