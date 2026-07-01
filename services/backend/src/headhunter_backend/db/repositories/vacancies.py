from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from headhunter_backend.api.schemas import VacancyAPISchema
from headhunter_backend.db.models import VacancyORM, search_vacancies_table
from headhunter_backend.log import get_logger

logger = get_logger(__name__)


class VacancyRepository:
    @classmethod
    async def create(cls, session: AsyncSession, vacancy: VacancyORM) -> VacancyORM:
        logger.info(f"Insert into DB vacancy: {vacancy.id}")
        session.add(vacancy)
        logger.info("Commiting insertion")
        await session.commit()
        return vacancy

    @classmethod
    async def upsert(
        cls, session: AsyncSession, vacancy: VacancyAPISchema
    ) -> VacancyORM:
        # id is excluded so SQLite autoincrement assigns it on insert and the
        # on_conflict_do_update path never touches the primary key.
        values = vacancy.model_dump(mode="json", exclude={"id"})
        stmt = sqlite_insert(VacancyORM).values(**values)
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

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, vacancy_id: int
    ) -> VacancyORM | None:
        logger.info(f"Get vacancy by id: {vacancy_id}")
        return await session.get(VacancyORM, vacancy_id)

    @classmethod
    async def get_by_apply_link(
        cls, session: AsyncSession, apply_link: str
    ) -> VacancyORM | None:
        logger.info(f"Get vacancy by apply link: {apply_link}")
        stmt = select(VacancyORM).where(VacancyORM.apply_link == apply_link)
        result = await session.execute(statement=stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def list_all(
        cls, session: AsyncSession, search_id: str | None = None
    ) -> Sequence[VacancyORM]:
        logger.info("List vacancies")
        if search_id is None:
            result = await session.execute(select(VacancyORM))
            return result.scalars().all()
        stmt = (
            select(VacancyORM)
            .join(
                search_vacancies_table,
                VacancyORM.id == search_vacancies_table.c.vacancy_id,
            )
            .where(search_vacancies_table.c.search_id == search_id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def link_to_search(
        cls, session: AsyncSession, search_id: str, vacancy_id: int
    ) -> None:
        # Idempotently attach a vacancy to a search (M2M).
        stmt = (
            sqlite_insert(search_vacancies_table)
            .values(search_id=search_id, vacancy_id=vacancy_id)
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)

    @classmethod
    async def delete(cls, session: AsyncSession, vacancy_id: int) -> bool:
        vacancy = await cls.get_by_id(session=session, vacancy_id=vacancy_id)
        if vacancy is None:
            logger.error(
                f"Failed to delete vacancy by id: {vacancy_id}. Error: not found"
            )
            return False
        logger.info(f"Deleting vacancy by id: {vacancy_id}")
        await session.delete(vacancy)
        logger.info("Committing delete")
        await session.commit()
        return True
