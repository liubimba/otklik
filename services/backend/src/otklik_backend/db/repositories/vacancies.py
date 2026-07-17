from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import VacancyAPISchema
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.models import (
    ApplicationORM,
    VacancyORM,
    search_vacancies_table,
)
from otklik_backend.log import get_logger

logger = get_logger(__name__)

_SEARCHABLE_COLUMNS = (
    VacancyORM.title,
    VacancyORM.company_name,
    VacancyORM.description,
)


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


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

    @staticmethod
    def _search_conditions(search: str) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        for word in search.split():
            pattern = _like_pattern(word.lower())
            conditions.append(
                or_(
                    *[
                        func.py_lower(column).like(pattern, escape="\\")
                        for column in _SEARCHABLE_COLUMNS
                    ]
                )
            )
        return conditions

    @classmethod
    async def list_with_status(
        cls,
        session: AsyncSession,
        statuses: Sequence[ProcessingState] | None = None,
        include_unapplied: bool = False,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[tuple[VacancyORM, ProcessingState | None]], int]:
        logger.info(
            "List vacancies with status",
            statuses=statuses,
            include_unapplied=include_unapplied,
            search=search,
            limit=limit,
            offset=offset,
        )

        join_on = ApplicationORM.vacancy_id == VacancyORM.id

        status_conditions: list[ColumnElement[bool]] = []
        if statuses:
            status_conditions.append(ApplicationORM.status.in_(statuses))
        if include_unapplied:
            status_conditions.append(
                or_(
                    ApplicationORM.status.is_(None),
                    ApplicationORM.status == ProcessingState.PARSED,
                )
            )

        filters: list[ColumnElement[bool]] = []
        if status_conditions:
            filters.append(or_(*status_conditions))
        if search and search.strip():
            filters.extend(cls._search_conditions(search))

        count_stmt = (
            select(func.count())
            .select_from(VacancyORM)
            .outerjoin(ApplicationORM, join_on)
        )
        page_stmt = select(VacancyORM, ApplicationORM.status).outerjoin(
            ApplicationORM, join_on
        )
        if filters:
            count_stmt = count_stmt.where(*filters)
            page_stmt = page_stmt.where(*filters)

        total: int = (await session.execute(count_stmt)).scalar_one()

        page_stmt = page_stmt.order_by(VacancyORM.id.desc()).limit(limit).offset(offset)

        rows = (await session.execute(page_stmt)).all()
        return [(row[0], row[1]) for row in rows], total

    @classmethod
    async def link_to_search(
        cls, session: AsyncSession, search_id: str, vacancy_id: int
    ) -> None:
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
