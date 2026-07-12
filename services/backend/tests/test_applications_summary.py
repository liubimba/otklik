from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.repositories.applications import ApplicationRepository
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
