from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from headhunter_backend.db.models import Vacancy
from collections.abc import Sequence
from headhunter_backend.log import get_logger

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
