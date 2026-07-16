from fastapi import APIRouter
from otklik_backend.api.schemas import SettingsAPISchema
from otklik_backend.api.dependencies import SessionDep, AILayerDep
from otklik_backend.db.converters import settings_to_schema, settings_to_orm
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository

settings_router: APIRouter = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("")
async def get_settings_api(session: SessionDep) -> SettingsAPISchema:
    settings: SettingsORM = await SettingsRepository.get(session=session)
    return settings_to_schema(orm=settings)


@settings_router.put("")
async def update_settings_api(
    session: SessionDep, new_settings: SettingsAPISchema, ai_layer: AILayerDep
) -> SettingsAPISchema:
    settings: SettingsORM = await SettingsRepository.update(
        session=session, new_settings=settings_to_orm(new_settings)
    )
    ai_layer.rebuild(deployments=[d.resolve() for d in settings.llm_deployments])
    return settings_to_schema(orm=settings)
