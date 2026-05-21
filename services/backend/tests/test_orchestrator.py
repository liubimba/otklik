from headhunter_backend.orchestrator.queue import Orchestrator
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from headhunter_backend.db.models import Application
from headhunter_backend.db.crud import create_application, create_vacancy
from headhunter_backend.db.converters import vacancy_to_orm
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.domain.enums import ProcessingState


async def test_recover_from_db_pushes_applications(
    fake_orchestrator: Orchestrator, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    applications: list[Application] = []
    async with session_factory() as session:
        for _ in range(4):
            await create_vacancy(
                session=session,
                vacancy=vacancy_to_orm(
                    VacancyModel(
                        title="test", apply_link=f"test{_}", description="test"
                    )
                ),
            )

        applications.append(await create_application(session=session, vacancy_id=1))
        applications.append(await create_application(session=session, vacancy_id=2))

        application: Application = await create_application(
            session=session, vacancy_id=3
        )
        application.status = ProcessingState.LETTER_SENT
        await session.commit()

        application: Application = await create_application(
            session=session, vacancy_id=4
        )
        application.status = ProcessingState.SKIPPED
        await session.commit()

        recovered_count: int = await fake_orchestrator.recover_from_db(session=session)
        assert recovered_count == len(applications)
        assert fake_orchestrator.qsize() == len(applications)
        assert {
            await fake_orchestrator.get_next(),
            await fake_orchestrator.get_next(),
        } == {applications[0].id, applications[1].id}
        assert fake_orchestrator.qsize() == 0


async def test_enqueue_then_get_next(fake_orchestrator: Orchestrator) -> None:
    await fake_orchestrator.enqueue(application_id=42)
    assert fake_orchestrator.qsize() == 1
    next_id: int = await fake_orchestrator.get_next()
    assert next_id == 42
    assert fake_orchestrator.qsize() == 0
