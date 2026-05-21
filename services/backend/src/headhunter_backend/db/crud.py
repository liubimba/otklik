from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from headhunter_backend.db.models import Vacancy, Application
from collections.abc import Sequence
from headhunter_backend.log import get_logger
from headhunter_backend.domain.enums import ProcessingState
from headhunter_backend.orchestrator.state_machine import (
    ProcessingStateMachine,
    ApplicationEvent,
)

logger = get_logger(__name__)


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
