from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import SettingsAPISchema
from otklik_backend.db.converters import settings_to_orm
from otklik_backend.db.models import SettingsORM


class SettingsRepository:
    @classmethod
    async def get(cls, session: AsyncSession) -> SettingsORM:
        settings: SettingsORM | None = await session.get(SettingsORM, 1)
        if settings is None:
            settings = settings_to_orm(schema=SettingsAPISchema(), deployments=[])
            session.add(settings)
            await session.commit()
        return settings

    @classmethod
    async def update(
        cls, session: AsyncSession, new_settings: SettingsORM
    ) -> SettingsORM:
        settings = await cls.get(session=session)
        for col in SettingsORM.__table__.columns:
            if col.primary_key:
                continue
            setattr(settings, col.name, getattr(new_settings, col.name))
        await session.commit()
        return settings
