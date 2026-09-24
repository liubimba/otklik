from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository


async def _seed_application(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy: VacancyAPISchema,
    status: ProcessingState,
) -> None:
    async with session_factory() as session:
        created = await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(schema=vacancy)
        )
        application = await ApplicationRepository.create(
            session=session, vacancy_id=created.id
        )
        application.status = status
        await session.commit()


async def test_count_in_states_counts_only_requested_states(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed_application(
        session_factory, vacancy_model, ProcessingState.LETTER_SENDING
    )

    async with session_factory() as session:
        assert (
            await ApplicationRepository.count_in_states(
                session=session,
                states=[
                    ProcessingState.LETTER_QUEUED,
                    ProcessingState.LETTER_SENDING,
                ],
            )
            == 1
        )
        assert (
            await ApplicationRepository.count_in_states(
                session=session, states=[ProcessingState.LETTER_QUEUED]
            )
            == 0
        )


async def test_count_in_states_is_zero_for_empty_states(
    session_factory: async_sessionmaker[AsyncSession],
    vacancy_model: VacancyAPISchema,
) -> None:
    await _seed_application(
        session_factory, vacancy_model, ProcessingState.LETTER_SENDING
    )
    async with session_factory() as session:
        assert (
            await ApplicationRepository.count_in_states(session=session, states=[]) == 0
        )
