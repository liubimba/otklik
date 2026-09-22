from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import SettingsAPISchema
from otklik_backend.db.converters import settings_to_orm
from otklik_backend.db.models import SettingsORM


class SettingsRepository:
    _PRESERVED_ON_UPDATE = frozenset({"board_prompts"})

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
            if col.primary_key or col.name in cls._PRESERVED_ON_UPDATE:
                continue
            setattr(settings, col.name, getattr(new_settings, col.name))
        await session.commit()
        return settings

    @classmethod
    async def set_board_prompt(
        cls, session: AsyncSession, board_value: str, entry: dict[str, str] | None
    ) -> SettingsORM:
        settings = await cls.get(session=session)
        prompts = dict(settings.board_prompts or {})
        if entry is None:
            prompts.pop(board_value, None)
        else:
            prompts[board_value] = entry
        settings.board_prompts = prompts
        await session.commit()
        return settings
