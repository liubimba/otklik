from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import (
    ProcessingState,
    SearchStatusAPISchema,
    VacancyAPISchema,
)
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.state_machine import ApplicationEvent


async def _seed(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy: VacancyAPISchema,
    *events: ApplicationEvent,
) -> None:
    """Создаёт вакансию с заявкой и прогоняет её по цепочке событий."""
    async with session_factory() as session:
        created = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        application = await ApplicationRepository.create(
            session=session, vacancy_id=created.id
        )
        for event in events:
            await ApplicationRepository.transition(
                session=session, application_id=application.id, to_state=event
            )


async def test_counts_zero_when_there_are_no_applications(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert await ApplicationRepository.count_needs_attention(session=session) == 0


async def test_counts_letter_ready_reviewing_and_error(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    # LETTER_READY — письмо готово, ждёт решения
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/1"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )
    # LETTER_REVIEWING — пользователь открыл письмо
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/2"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
        ApplicationEvent.SEND_FOR_REVIEW,
    )
    # ERROR — упало, требует внимания
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/3"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.FAIL,
    )
    # LETTER_PENDING — работа идёт, пользователю делать нечего: НЕ считаем
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/4"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
    )

    async with session_factory() as session:
        assert await ApplicationRepository.count_needs_attention(session=session) == 3


async def test_terminal_states_are_not_counted(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/1"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
        ApplicationEvent.SEND_FOR_REVIEW,
        ApplicationEvent.SKIP,
    )

    async with session_factory() as session:
        count = await ApplicationRepository.count_needs_attention(session=session)

    assert count == 0
    async with session_factory() as session:
        applications = await ApplicationRepository.list_all(session=session)
        assert applications[0].status is ProcessingState.SKIPPED


async def test_summary_endpoint_returns_zero_on_empty_db(client) -> None:
    response: Response = client.get("/api/v1/applications/summary")

    assert response.status_code == 200
    assert response.json() == {"needs_attention": 0}


async def test_summary_endpoint_counts_applications_awaiting_the_user(
    client,
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    # `client` already inserts a vacancy from the unmodified `vacancy_model`
    # fixture (see conftest.py) — reusing it here would collide on the unique
    # `apply_link`, so this seeds a second vacancy with a distinct link.
    await _seed(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/999"}),
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )

    response: Response = client.get("/api/v1/applications/summary")

    assert response.status_code == 200
    assert response.json() == {"needs_attention": 1}


# --- Scoped to one search ------------------------------------------------------
#
# «Очередь вакансий» only ever lists the LATEST search, so a global count on that
# row points at work the screen may not show: start a new search and the previous
# one's unfinished letters drop off the list while still being counted. The badge
# has to be able to count within a single search.


async def _seed_search_with_application(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy: VacancyAPISchema,
    search_id: str,
    *events: ApplicationEvent,
) -> None:
    """A search, a vacancy linked to it, and an application walked to a state."""
    async with session_factory() as session:
        # Several vacancies can belong to one search — only create it once.
        existing = {
            s.id for s in await SearchHistoryRepository.list_all(session=session)
        }
        if search_id not in existing:
            await SearchHistoryRepository.create(
                session=session,
                search_id=search_id,
                url="https://hh.ru/search/vacancy",
                max_vacancies=10,
                max_pages=1,
                search_status=SearchStatusAPISchema.FINISHED,
            )
        created = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        await VacancyRepository.link_to_search(
            session=session, search_id=search_id, vacancy_id=created.id
        )
        await session.commit()

        application = await ApplicationRepository.create(
            session=session, vacancy_id=created.id
        )
        for event in events:
            await ApplicationRepository.transition(
                session=session, application_id=application.id, to_state=event
            )


async def test_counts_only_the_requested_search(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed_search_with_application(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/101"}),
        "search-old",
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )
    await _seed_search_with_application(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/201"}),
        "search-new",
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )
    await _seed_search_with_application(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/202"}),
        "search-new",
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.FAIL,
    )

    async with session_factory() as session:
        assert await ApplicationRepository.count_needs_attention(session=session) == 3
        assert (
            await ApplicationRepository.count_needs_attention(
                session=session, search_id="search-new"
            )
            == 2
        )
        assert (
            await ApplicationRepository.count_needs_attention(
                session=session, search_id="search-old"
            )
            == 1
        )
        assert (
            await ApplicationRepository.count_needs_attention(
                session=session, search_id="search-missing"
            )
            == 0
        )


async def test_summary_endpoint_scopes_to_the_latest_search(
    client,
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed_search_with_application(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/301"}),
        "search-old",
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )
    await _seed_search_with_application(
        session_factory,
        vacancy_model.model_copy(update={"apply_link": "https://hh.ru/vacancy/302"}),
        "search-new",
        ApplicationEvent.ENQUEUE_FOR_LETTER,
        ApplicationEvent.LETTER_GENERATED,
    )

    # No param — global, same as before.
    assert client.get("/api/v1/applications/summary").json() == {"needs_attention": 2}
    # "latest" — only the most recent search, mirroring GET /vacancies/.
    assert client.get("/api/v1/applications/summary?search_id=latest").json() == {
        "needs_attention": 1
    }
    # "all" — explicit global.
    assert client.get("/api/v1/applications/summary?search_id=all").json() == {
        "needs_attention": 2
    }
    # An explicit id.
    assert client.get("/api/v1/applications/summary?search_id=search-old").json() == {
        "needs_attention": 1
    }


async def test_summary_latest_is_zero_when_no_search_ran_yet(client) -> None:
    assert client.get("/api/v1/applications/summary?search_id=latest").json() == {
        "needs_attention": 0
    }
