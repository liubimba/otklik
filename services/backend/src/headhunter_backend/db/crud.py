from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from headhunter_backend.db.models import (
    VacancyORM,
    ApplicationORM,
    CoverLetterORM,
    SettingsORM,
    RateLimitEventORM,
    SearchHistoryORM,
)
from headhunter_backend.api.schemas import SettingsAPISchema
from collections.abc import Sequence
from headhunter_backend.log import get_logger
from headhunter_backend.domain.enums import ProcessingState
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.converters import settings_to_orm
from headhunter_backend.orchestrator.state_machine import (
    ProcessingStateMachine,
    ApplicationEvent,
)
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from headhunter_backend.api.schemas import SearchStatusAPISchema
from typing import Any

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
        settings = settings_to_orm(model=SettingsAPISchema())
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


async def create_vacancy(session: AsyncSession, vacancy: VacancyORM) -> VacancyORM:
    logger.info(f"Insert into DB vacancy: {vacancy.id}")
    session.add(vacancy)
    logger.info("Commiting insertion")
    await session.commit()
    return vacancy


async def upsert_vacancy(session: AsyncSession, vacancy: VacancyModel) -> VacancyORM:
    stmt = sqlite_insert(VacancyORM).values(**vacancy.model_dump(mode="json"))
    stmt = stmt.on_conflict_do_update(
        index_elements=[VacancyORM.apply_link],
        set_={
            col: stmt.excluded[col]
            for col in [
                "title",
                "description",
                "salary",
                "company_stars",
                "work_location",
                "updated_at",
                "published_at",
                "work_experience",
                "work_formats",
                "employment_types",
            ]
        },
    )
    await session.execute(stmt)
    result = await session.execute(
        select(VacancyORM).where(VacancyORM.apply_link == vacancy.apply_link)
    )
    return result.scalar_one()


async def get_vacancy(session: AsyncSession, vacancy_id: int) -> VacancyORM | None:
    logger.info(f"Get vacancy by id: {vacancy_id}")
    return await session.get(VacancyORM, vacancy_id)


async def get_vacancy_by_apply_link(
    session: AsyncSession, apply_link: str
) -> VacancyORM | None:
    logger.info(f"Get vacancy by apply link: {apply_link}")
    stmt = select(VacancyORM).where(VacancyORM.apply_link == apply_link)
    result = await session.execute(statement=stmt)
    return result.scalar_one_or_none()


async def list_vacancies(session: AsyncSession) -> Sequence[VacancyORM]:
    logger.info("List vacancies")
    result = await session.execute(select(VacancyORM))
    return result.scalars().all()


async def delete_vacancy(session: AsyncSession, vacancy_id: int) -> bool:
    vacancy: VacancyORM | None = await get_vacancy(
        session=session, vacancy_id=vacancy_id
    )
    if vacancy is None:
        logger.error(f"Failed to delete vacancy by id: {vacancy_id}. Error: not found")
        return False
    logger.info(f"Deleting vacancy by id: {vacancy_id}")
    await session.delete(vacancy)
    logger.info("Committing delete")
    await session.commit()
    return True


async def create_application(session: AsyncSession, vacancy_id: int) -> ApplicationORM:
    logger.info(f"Create new application for vacancy id: {vacancy_id}")
    application: ApplicationORM = ApplicationORM(
        vacancy_id=vacancy_id, status=ProcessingState.PARSED
    )
    session.add(application)
    await session.commit()
    return application


async def get_application_by_id(
    session: AsyncSession, application_id: int
) -> ApplicationORM | None:
    application: ApplicationORM | None = await session.get(
        ApplicationORM, application_id
    )
    return application


async def get_application_by_vacancy_id(
    session: AsyncSession, vacancy_id: int
) -> ApplicationORM | None:
    result = await session.execute(
        select(ApplicationORM).where(ApplicationORM.vacancy_id == vacancy_id).limit(1)
    )
    return result.scalar_one_or_none()


async def transition_application(
    session: AsyncSession, application_id: int, to_state: ApplicationEvent
) -> ApplicationORM | None:
    application: ApplicationORM | None = await get_application_by_id(
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


async def list_applications(session: AsyncSession) -> Sequence[ApplicationORM]:
    result = await session.execute(select(ApplicationORM))
    return result.scalars().all()


async def list_active_applications(session: AsyncSession) -> Sequence[ApplicationORM]:
    result = await session.execute(
        select(ApplicationORM).where(
            ApplicationORM.status.not_in(
                [ProcessingState.SKIPPED, ProcessingState.LETTER_SENT]
            )
        )
    )
    return result.scalars().all()


async def create_cover_letter(
    session: AsyncSession, application_id: int, text: str
) -> CoverLetterORM:
    latest_cover_letter: CoverLetterORM | None = await get_latest_cover_letter(
        session=session, application_id=application_id
    )
    version_cover_letter: int = (
        1 if latest_cover_letter is None else latest_cover_letter.version + 1
    )
    cover_letter: CoverLetterORM = CoverLetterORM(
        application_id=application_id, text=text, version=version_cover_letter
    )
    session.add(cover_letter)
    await session.commit()
    return cover_letter


async def get_latest_cover_letter(
    session: AsyncSession, application_id: int
) -> CoverLetterORM | None:
    stmt = (
        select(CoverLetterORM)
        .where(CoverLetterORM.application_id == application_id)
        .order_by(CoverLetterORM.version.desc())
        .limit(1)
    )
    result = await session.execute(statement=stmt)
    return result.scalar_one_or_none()


async def create_search_history(
    session: AsyncSession,
    search_id: str,
    url: str,
    max_vacancies: int,
    max_pages: int,
    search_status: SearchStatusAPISchema,
) -> SearchHistoryORM:
    search_history: SearchHistoryORM = SearchHistoryORM(
        id=search_id,
        url=url,
        max_vacancies=max_vacancies,
        max_pages=max_pages,
        status=search_status,
    )
    session.add(search_history)
    await session.commit()
    return search_history


async def list_search_history(session: AsyncSession) -> Sequence[SearchHistoryORM]:
    result = await session.execute(select(SearchHistoryORM))
    return result.scalars().all()


async def update_search_history(
    session: AsyncSession,
    search_id: str,
    **kwargs: Any,
) -> SearchHistoryORM | None:
    row = await session.get(SearchHistoryORM, search_id)
    if row is None:
        return None
    allowed = {"status", "parsed_pages", "parsed_vacancies", "finished_at", "error"}
    for key, value in kwargs.items():
        if key not in allowed:
            raise ValueError(f"Cannot update column: {key}")
        setattr(row, key, value)
    await session.commit()
    return row
