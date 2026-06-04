from fastapi import APIRouter
from headhunter_backend.api.schemas import SettingsAPISchema
from headhunter_backend.api.dependencies import SessionDep, AILayerDep
from headhunter_backend.db.converters import settings_to_schema, settings_to_orm
from headhunter_backend.db.models import SettingsORM
from headhunter_backend.db.crud import get_settings, update_settings

settings_router: APIRouter = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("")
async def get_settings_api(session: SessionDep) -> SettingsAPISchema:
    settings: SettingsORM = await get_settings(session=session)
    return settings_to_schema(orm=settings)


@settings_router.put("")
async def update_settings_api(
    session: SessionDep, new_settings: SettingsAPISchema, ai_layer: AILayerDep
) -> SettingsAPISchema:
    settings: SettingsORM = await update_settings(
        session=session, new_settings=settings_to_orm(new_settings)
    )
    ai_layer.rebuild(deployments=settings.llm_deployments)
    return settings_to_schema(orm=settings)
