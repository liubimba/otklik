from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from headhunter_backend.db.crud import upsert_vacancy
from headhunter_backend.db.models import VacancyORM
from headhunter_backend.api.schemas import VacancyAPISchema
from headhunter_backend.db.models import (
    ApplicationORM,
    CoverLetterORM,
    SearchHistoryORM,
)
from headhunter_backend.db.converters import vacancy_to_schema, vacancy_to_orm
from headhunter_backend.db.crud import (
    create_vacancy,
    get_vacancy,
    get_vacancy_by_apply_link,
    list_vacancies,
    delete_vacancy,
    create_cover_letter,
    get_latest_cover_letter,
    create_application,
    create_search_history,
    list_search_history,
    update_search_history,
    list_applications_by_status,
    transition_application,
)
from headhunter_backend.api.schemas import ProcessingState, SearchStatusAPISchema
from headhunter_backend.orchestrator.state_machine import ApplicationEvent


async def test_vacancy_crud(
    session_factory: async_sessionmaker[AsyncSession], vacancy_model: VacancyAPISchema
) -> None:
    async with session_factory() as session:
        created: VacancyORM = await create_vacancy(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )
        vacancy_id: int = created.id
        assert vacancy_id is not None

    async with session_factory() as session:
        by_id: VacancyORM = await get_vacancy(session=session, vacancy_id=vacancy_id)
        assert by_id is not None

        by_link: VacancyORM = await get_vacancy_by_apply_link(
            session=session, apply_link=vacancy_model.apply_link
        )
        assert by_link is not None

        assert len(await list_vacancies(session=session)) == 1

        assert by_id.work_formats == ["remote", "hybrid"]
        assert by_id.employment_types == ["full_time", "part_time"]

        # vacancy_model fixture has no id; the DB row always does.
        expected = vacancy_model.model_dump(exclude={"id"})
        assert vacancy_to_schema(row=by_id).model_dump(exclude={"id"}) == expected

    async with session_factory() as session:
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is True
        assert await get_vacancy(session=session, vacancy_id=vacancy_id) is None
        assert await delete_vacancy(session=session, vacancy_id=vacancy_id) is False


async def test_cover_letter_crud(
    session_factory: async_sessionmaker[AsyncSession], vacancy_model: VacancyAPISchema
) -> None:
    async with session_factory() as session:
        created_vacancy: VacancyORM = await create_vacancy(
            session=session, vacancy=vacancy_to_orm(schema=vacancy_model)
        )
        vacancy_id: int = created_vacancy.id

        created_application: ApplicationORM = await create_application(
            session=session, vacancy_id=vacancy_id
        )
        application_id: int = created_application.id

        text: str = "Test"
        first_created: CoverLetterORM = await create_cover_letter(
            session=session, application_id=application_id, text=text
        )
        first_created_id: int = first_created.id

        assert first_created_id is not None
        assert first_created.text == text
        assert first_created.application_id == application_id
        assert first_created.version == 1

        text = text * 2
        second_created: CoverLetterORM = await create_cover_letter(
            session=session, application_id=application_id, text=text
        )

        assert second_created.id is not None
        assert second_created.id != first_created_id
        assert second_created.application_id == application_id
        assert second_created.version == 2
        assert second_created.text == text

        latest: CoverLetterORM = await get_latest_cover_letter(
            session=session, application_id=application_id
        )

        assert latest == second_created

        assert (
            await get_latest_cover_letter(session=session, application_id=999) is None
        )


async def test_upsert_inserts_new_vacancy(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        v = await upsert_vacancy(
            session=session,
            vacancy=VacancyAPISchema(
                title="Junior Dev",
                apply_link="https://hh.ru/vacancy/1",
                description="desc",
            ),
        )
        await session.commit()

        count = (await session.execute(select(func.count(VacancyORM.id)))).scalar_one()
        assert count == 1
        assert v.title == "Junior Dev"


async def test_upsert_updates_existing_vacancy(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    apply_link = "https://hh.ru/vacancy/42"
    async with session_factory() as session:
        await upsert_vacancy(
            session=session,
            vacancy=VacancyAPISchema(
                title="old",
                apply_link=apply_link,
                description="old",
                salary="100k",
            ),
        )
        await session.commit()

        await upsert_vacancy(
            session=session,
            vacancy=VacancyAPISchema(
                title="new",
                apply_link=apply_link,
                description="new",
                salary="150k",
            ),
        )
        await session.commit()

        count = (await session.execute(select(func.count(VacancyORM.id)))).scalar_one()
        assert count == 1

        row = (
            await session.execute(
                select(VacancyORM).where(VacancyORM.apply_link == apply_link)
            )
        ).scalar_one()
        assert row.title == "new"
        assert row.description == "new"
        assert row.salary == "150k"


async def test_upsert_preserves_id_and_apply_link(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    apply_link = "https://hh.ru/vacancy/100"
    async with session_factory() as session:
        first = await upsert_vacancy(
            session=session,
            vacancy=VacancyAPISchema(title="A", apply_link=apply_link, description="a"),
        )
        await session.commit()
        original_id = first.id

        second = await upsert_vacancy(
            session=session,
            vacancy=VacancyAPISchema(title="B", apply_link=apply_link, description="b"),
        )
        await session.commit()

        assert second.id == original_id
        assert second.apply_link == apply_link


async def test_create_search_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        search_id: str = "test"
        max_pages: int = 2
        max_vacancies: int = 4
        search_status: SearchStatusAPISchema = SearchStatusAPISchema.PENDING
        url: str = "hh.ru"
        search_history: SearchHistoryORM = await create_search_history(
            session=session,
            search_id=search_id,
            url=url,
            search_status=search_status,
            max_vacancies=max_vacancies,
            max_pages=max_pages,
        )
        assert search_history.id == search_id
        assert max_pages == search_history.max_pages
        assert max_vacancies == search_history.max_vacancies
        assert search_status == search_history.status
        assert url == search_history.url


async def test_list_search_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        search_id: str = "test"
        max_pages: int = 2
        max_vacancies: int = 4
        search_status: SearchStatusAPISchema = SearchStatusAPISchema.PENDING
        url: str = "hh.ru"
        search_history: SearchHistoryORM = await create_search_history(
            session=session,
            search_id=search_id,
            url=url,
            search_status=search_status,
            max_vacancies=max_vacancies,
            max_pages=max_pages,
        )
        result = await list_search_history(session=session)
        assert len(result) == 1
        assert result[0] == search_history


async def test_list_applications_by_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        v_pending = await create_vacancy(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="P",
                    apply_link="https://hh.ru/p",
                    description="d",
                )
            ),
        )
        v_ready = await create_vacancy(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="R",
                    apply_link="https://hh.ru/r",
                    description="d",
                )
            ),
        )
        v_parsed = await create_vacancy(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(
                    title="X",
                    apply_link="https://hh.ru/x",
                    description="d",
                )
            ),
        )

        app_pending = await create_application(session=session, vacancy_id=v_pending.id)
        await transition_application(
            session=session,
            application_id=app_pending.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )

        app_ready = await create_application(session=session, vacancy_id=v_ready.id)
        await transition_application(
            session=session,
            application_id=app_ready.id,
            to_state=ApplicationEvent.ENQUEUE_FOR_LETTER,
        )
        await transition_application(
            session=session,
            application_id=app_ready.id,
            to_state=ApplicationEvent.LETTER_GENERATED,
        )

        await create_application(session=session, vacancy_id=v_parsed.id)

        pending = await list_applications_by_status(
            session=session, status=ProcessingState.LETTER_PENDING
        )
        assert {a.vacancy_id for a in pending} == {v_pending.id}

        ready = await list_applications_by_status(
            session=session, status=ProcessingState.LETTER_READY
        )
        assert {a.vacancy_id for a in ready} == {v_ready.id}

        parsed = await list_applications_by_status(
            session=session, status=ProcessingState.PARSED
        )
        assert {a.vacancy_id for a in parsed} == {v_parsed.id}

        skipped = await list_applications_by_status(
            session=session, status=ProcessingState.SKIPPED
        )
        assert list(skipped) == []


async def test_search_history_update(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        search_id: str = "test"
        max_pages: int = 2
        max_vacancies: int = 4
        search_status: SearchStatusAPISchema = SearchStatusAPISchema.PENDING
        parsed_vacancies: int = 2
        url: str = "hh.ru"
        await create_search_history(
            session=session,
            search_id=search_id,
            url=url,
            search_status=search_status,
            max_vacancies=max_vacancies,
            max_pages=max_pages,
        )
        await update_search_history(
            session=session, search_id=search_id, parsed_vacancies=parsed_vacancies
        )
