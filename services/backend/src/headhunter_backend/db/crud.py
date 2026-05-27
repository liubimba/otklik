from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from headhunter_backend.db.models import (
    Vacancy,
    Application,
    CoverLetter,
    SettingsORM,
    RateLimitEventORM,
)
from headhunter_backend.api.schemas import Settings
from collections.abc import Sequence
from headhunter_backend.log import get_logger
from headhunter_backend.domain.enums import ProcessingState
from headhunter_backend.db.converters import settings_to_orm
from headhunter_backend.orchestrator.state_machine import (
    ProcessingStateMachine,
    ApplicationEvent,
)
from datetime import datetime

logger = get_logger(__name__)


async def log_submission(session: AsyncSession) -> None:
    session.add(RateLimitEventORM())
    await session.commit()


async def count_submissions_since(session: AsyncSession, since: datetime) -> int:
    stmt = select(func.count(RateLimitEventORM.id)).where(
        RateLimitEventORM.occurred_at > since
    )
    result = await session.execute(statement=stmt)
    return result.scalar_one()


async def get_settings(session: AsyncSession) -> SettingsORM:
    settings: SettingsORM | None = await session.get(SettingsORM, 1)
    if settings is None:
        settings = settings_to_orm(model=Settings())
        session.add(settings)
        await session.commit()
    return settings


async def update_settings(
    session: AsyncSession, new_settings: SettingsORM
) -> SettingsORM:
    settings: SettingsORM = await get_settings(session=session)
    settings.daily_limit = new_settings.daily_limit
    settings.delay_jitter_ms = new_settings.delay_jitter_ms
    settings.hourly_limit = new_settings.hourly_limit
    settings.letter_style = new_settings.letter_style
    settings.resume_text = new_settings.resume_text
    settings.min_delay_ms = new_settings.min_delay_ms
    await session.commit()
    return settings


async def create_vacancy(session: AsyncSession, vacancy: Vacancy) -> Vacancy:
    logger.info(f"Insert into DB vacancy: {vacancy.id}")
    session.add(vacancy)
    logger.info("Commiting insertion")
    await session.commit()
    return vacancy


async def get_vacancy(session: AsyncSession, vacancy_id: int) -> Vacancy | None:
    logger.info(f"Get vacancy by id: {vacancy_id}")
    return await session.get(Vacancy, vacancy_id)


async def get_vacancy_by_apply_link(
    session: AsyncSession, apply_link: str
) -> Vacancy | None:
    logger.info(f"Get vacancy by apply link: {apply_link}")
    stmt = select(Vacancy).where(Vacancy.apply_link == apply_link)
    result = await session.execute(statement=stmt)
    return result.scalar_one_or_none()


async def list_vacancies(session: AsyncSession) -> Sequence[Vacancy]:
    logger.info("List vacancies")
    result = await session.execute(select(Vacancy))
    return result.scalars().all()


async def delete_vacancy(session: AsyncSession, vacancy_id: int) -> bool:
    vacancy: Vacancy | None = await get_vacancy(session=session, vacancy_id=vacancy_id)
    if vacancy is None:
        logger.error(f"Failed to delete vacancy by id: {vacancy_id}. Error: not found")
        return False
    logger.info(f"Deleting vacancy by id: {vacancy_id}")
    await session.delete(vacancy)
    logger.info("Committing delete")
    await session.commit()
    return True


async def create_application(session: AsyncSession, vacancy_id: int) -> Application:
    logger.info(f"Create new application for vacancy id: {vacancy_id}")
    application: Application = Application(
        vacancy_id=vacancy_id, status=ProcessingState.PARSED
    )
    session.add(application)
    await session.commit()
    return application


async def get_application_by_id(
    session: AsyncSession, application_id: int
) -> Application | None:
    application: Application | None = await session.get(Application, application_id)
    return application


async def get_application_by_vacancy_id(
    session: AsyncSession, vacancy_id: int
) -> Application | None:
    result = await session.execute(
        select(Application).where(Application.vacancy_id == vacancy_id).limit(1)
    )
    return result.scalar_one_or_none()


async def transition_application(
    session: AsyncSession, application_id: int, to_state: ApplicationEvent
) -> Application | None:
    application: Application | None = await get_application_by_id(
        session=session, application_id=application_id
    )
    if application is None:
        return None
    state_machine: ProcessingStateMachine = ProcessingStateMachine(
        start_value=application.status
    )
    state_machine.send(to_state.value)
    application.status = ProcessingState(state_machine.current_state_value)
    await session.commit()
    logger.info(
        "Transited application state", application_id=application_id, to_state=to_state
    )
    return application


async def list_applications(session: AsyncSession) -> Sequence[Application]:
    result = await session.execute(select(Application))
    return result.scalars().all()


async def list_active_applications(session: AsyncSession) -> Sequence[Application]:
    result = await session.execute(
        select(Application).where(
            Application.status.not_in(
                [ProcessingState.SKIPPED, ProcessingState.LETTER_SENT]
            )
        )
    )
    return result.scalars().all()


async def create_cover_letter(
    session: AsyncSession, application_id: int, text: str
) -> CoverLetter:
    latest_cover_letter: CoverLetter | None = await get_latest_cover_letter(
        session=session, application_id=application_id
    )
    version_cover_letter: int = (
        1 if latest_cover_letter is None else latest_cover_letter.version + 1
    )
    cover_letter: CoverLetter = CoverLetter(
        application_id=application_id, text=text, version=version_cover_letter
    )
    session.add(cover_letter)
    await session.commit()
    return cover_letter


async def get_latest_cover_letter(
    session: AsyncSession, application_id: int
) -> CoverLetter | None:
    stmt = (
        select(CoverLetter)
        .where(CoverLetter.application_id == application_id)
        .order_by(CoverLetter.version.desc())
        .limit(1)
    )
    result = await session.execute(statement=stmt)
    return result.scalar_one_or_none()
