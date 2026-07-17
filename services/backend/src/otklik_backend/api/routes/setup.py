import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import SecretStr

from otklik_backend.ai.deployment import LLMDeployment, ResolvedDeployment
from otklik_backend.api.dependencies import (
    ChromiumGateDep,
    AILayerDep,
    BenchmarkRunnerDep,
    ClaudeCodeGateDep,
    DeploymentSecretsDep,
    HardwareProbeDep,
    OllamaGateDep,
    SessionDep,
)
from otklik_backend.api.schemas import (
    ClaudeModelOption,
    ClaudeSetupStateAPISchema,
    LLMDeploymentWriteAPISchema,
    LocalSetupStateAPISchema,
    SettingsAPISchema,
    SetupStateAPISchema,
    TrialRequestAPISchema,
)
from otklik_backend.db.converters import settings_to_orm, settings_to_schema
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.log import get_logger
from otklik_backend.setup.benchmark import BenchmarkResult
from otklik_backend.setup.cloud_catalog import CloudCatalog, CloudModelOption
from otklik_backend.setup.constants import (
    CLAUDE_CODE_DEFAULT_MODEL,
    CLAUDE_CODE_MODEL_OPTIONS,
    CLOUD_MODEL,
    LOCAL_MODEL,
    LOCAL_MODEL_TAG,
)
from otklik_backend.browser.chromium_gate import ChromiumInstallError
from otklik_backend.setup.ollama import OllamaPullError

log = get_logger(__name__)

setup_router = APIRouter(prefix="/setup", tags=["setup"])


@setup_router.get("/state")
async def setup_state(
    session: SessionDep,
    hardware: HardwareProbeDep,
    ollama: OllamaGateDep,
    claude: ClaudeCodeGateDep,
    chromium: ChromiumGateDep,
) -> SetupStateAPISchema:
    settings: SettingsORM = await SettingsRepository.get(session=session)
    return SetupStateAPISchema(
        hardware=hardware.probe(),
        ollama=await ollama.state(),
        has_deployment=any(item.is_usable() for item in settings.llm_deployments),
        local_model=LOCAL_MODEL,
        cloud_model=CLOUD_MODEL,
        claude_available=claude.credentials_present(),
        chromium_installed=chromium.is_installed(),
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


@setup_router.get("/claude")
async def setup_claude(claude: ClaudeCodeGateDep) -> ClaudeSetupStateAPISchema:
    return ClaudeSetupStateAPISchema(
        claude_state=await claude.state(),
        default_model=CLAUDE_CODE_DEFAULT_MODEL,
        model_options=[
            ClaudeModelOption(model=model, label=label)
            for model, label in CLAUDE_CODE_MODEL_OPTIONS
        ],
    )


@setup_router.post("/pull")
async def setup_pull(ollama: OllamaGateDep) -> StreamingResponse:
    async def frames() -> AsyncIterator[str]:
        try:
            async for progress in ollama.pull():
                yield f"data: {progress.model_dump_json()}\n\n"
        except OllamaPullError as exc:
            log.warning("Model pull failed", detail=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except Exception as exc:  # noqa: BLE001
            log.error("Model pull failed unexpectedly", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Model pull failed'})}\n\n"

    return StreamingResponse(frames(), media_type="text/event-stream")


@setup_router.post("/chromium")
async def setup_chromium(chromium: ChromiumGateDep) -> StreamingResponse:
    async def frames() -> AsyncIterator[str]:
        try:
            async for progress in chromium.install():
                yield f"data: {progress.model_dump_json()}\n\n"
        except ChromiumInstallError as exc:
            log.warning("Chromium install failed", detail=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except Exception as exc:  # noqa: BLE001
            log.error("Chromium install failed unexpectedly", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Chromium install failed'})}\n\n"

    return StreamingResponse(frames(), media_type="text/event-stream")


@setup_router.post("/trial")
async def setup_trial(
    runner: BenchmarkRunnerDep, request: TrialRequestAPISchema
) -> BenchmarkResult:
    resolved = ResolvedDeployment(
        deployment=LLMDeployment(
            model=request.deployment.model, api_base=request.deployment.api_base
        ),
        api_key=(
            SecretStr(request.deployment.api_key)
            if request.deployment.api_key
            else None
        ),
    )
    return await runner.run(deployment=resolved, deadline_sec=request.deadline_sec)


@setup_router.post("/deployment")
async def setup_deployment(
    session: SessionDep,
    ai_layer: AILayerDep,
    secrets: DeploymentSecretsDep,
    deployment: LLMDeploymentWriteAPISchema,
) -> SettingsAPISchema:
    current: SettingsORM = await SettingsRepository.get(session=session)
    probe = LLMDeployment(model=deployment.model, api_base=deployment.api_base)
    matched = next((d for d in current.llm_deployments if probe.matches(d)), None)
    rest = [d for d in current.llm_deployments if not probe.matches(d)]
    promoted = deployment.model_copy(update={"id": matched.id if matched else None})
    incoming = [promoted] + [
        LLMDeploymentWriteAPISchema(id=d.id, model=d.model, api_base=d.api_base)
        for d in rest
    ]
    deployments, plan = secrets.plan(current=current.llm_deployments, incoming=incoming)
    await secrets.commit(plan=plan)
    settings: SettingsAPISchema = settings_to_schema(orm=current)
    updated: SettingsORM = await SettingsRepository.update(
        session=session,
        new_settings=settings_to_orm(schema=settings, deployments=deployments),
    )
    ai_layer.rebuild(
        deployments=await secrets.resolve(deployments=updated.llm_deployments)
    )
    return settings_to_schema(orm=updated)


@setup_router.get("/cloud-models")
async def setup_cloud_models() -> list[CloudModelOption]:
    return CloudCatalog().options()
