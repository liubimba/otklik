from fastapi import APIRouter
from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.api.schemas import SettingsAPISchema, SettingsWriteAPISchema
from otklik_backend.api.dependencies import AILayerDep, DeploymentSecretsDep, SessionDep
from otklik_backend.db.converters import settings_to_schema, settings_to_orm
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.secrets.service import SecretPlan

settings_router: APIRouter = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("")
async def get_settings_api(session: SessionDep) -> SettingsAPISchema:
    settings: SettingsORM = await SettingsRepository.get(session=session)
    return settings_to_schema(orm=settings)


@settings_router.put("")
async def update_settings_api(
    session: SessionDep,
    new_settings: SettingsWriteAPISchema,
    ai_layer: AILayerDep,
    secrets: DeploymentSecretsDep,
) -> SettingsAPISchema:
    current: SettingsORM = await SettingsRepository.get(session=session)
    deployments: list[LLMDeployment]
    plan: SecretPlan
    deployments, plan = secrets.plan(
        current=current.llm_deployments, incoming=new_settings.llm.deployments
    )
    await secrets.commit(plan=plan)
    settings: SettingsORM = await SettingsRepository.update(
        session=session,
        new_settings=settings_to_orm(schema=new_settings, deployments=deployments),
    )
    ai_layer.rebuild(
        deployments=await secrets.resolve(deployments=settings.llm_deployments)
    )
    return settings_to_schema(orm=settings)
