from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import ProcessingState, VacancyAPISchema
from otklik_backend.core.state import ErrorDomain
from otklik_backend.db.converters import vacancy_to_orm
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.orchestrator.restart import (
    restart_counts,
    restart_generation,
    restart_submission,
)
from otklik_backend.orchestrator.state_service import StateTransitionService


async def _set_flags(
    session_factory: async_sessionmaker[AsyncSession],
    auto_generate: bool,
    auto_submit: bool,
) -> None:
    async with session_factory() as session:
        settings: SettingsORM = await SettingsRepository.get(session=session)
        settings.auto_generate = auto_generate
        settings.auto_submit = auto_submit
        await SettingsRepository.update(session=session, new_settings=settings)


async def _seed(
    session_factory: async_sessionmaker[AsyncSession],
    apply_link: str,
    status: ProcessingState,
    with_letter: bool = False,
    error_domain: ErrorDomain | None = None,
) -> int:
    async with session_factory() as session:
        vacancy = await VacancyRepository.create(
            session=session,
            vacancy=vacancy_to_orm(
                VacancyAPISchema(title="t", apply_link=apply_link, description="d")
            ),
        )
        app = await ApplicationRepository.create(session=session, vacancy_id=vacancy.id)
        app.status = status
        app.error_domain = error_domain
        await session.commit()
        if with_letter:
            await CoverLetterRepository.create(
                session=session,
                application_id=app.id,
                text="letter",
                source="manual",
            )
        return app.id


async def _status(
    session_factory: async_sessionmaker[AsyncSession], app_id: int
) -> ProcessingState:
    async with session_factory() as session:
        app = await ApplicationRepository.get_by_id(
            session=session, application_id=app_id
        )
        assert app is not None
        return app.status


async def test_restart_generation_reruns_interrupted_without_letter_and_model_errors(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=False)
    gen_interrupted = await _seed(
        session_factory, "l1", ProcessingState.INTERRUPTED, with_letter=False
    )
    gen_error = await _seed(
        session_factory,
        "l2",
        ProcessingState.ERROR,
        error_domain=ErrorDomain.MODEL,
    )
    submit_interrupted = await _seed(
        session_factory, "l3", ProcessingState.INTERRUPTED, with_letter=True
    )

    async with session_factory() as session:
        restarted = await restart_generation(session, fake_state_service)
        await session.commit()

    assert restarted == 2
    assert await _status(session_factory, gen_interrupted) == (
        ProcessingState.LETTER_PENDING
    )
    assert await _status(session_factory, gen_error) == ProcessingState.LETTER_PENDING
    assert await _status(session_factory, submit_interrupted) == (
        ProcessingState.INTERRUPTED
    )


async def test_restart_generation_does_nothing_when_auto_generate_off(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=False, auto_submit=True)
    app_id = await _seed(
        session_factory, "l1", ProcessingState.INTERRUPTED, with_letter=False
    )

    async with session_factory() as session:
        restarted = await restart_generation(session, fake_state_service)
        await session.commit()

    assert restarted == 0
    assert await _status(session_factory, app_id) == ProcessingState.INTERRUPTED


async def test_restart_submission_reruns_interrupted_with_letter_and_submit_errors(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=False, auto_submit=True)
    submit_interrupted = await _seed(
        session_factory, "l1", ProcessingState.INTERRUPTED, with_letter=True
    )
    submit_error = await _seed(
        session_factory,
        "l2",
        ProcessingState.ERROR,
        error_domain=ErrorDomain.SUBMISSION,
    )
    gen_interrupted = await _seed(
        session_factory, "l3", ProcessingState.INTERRUPTED, with_letter=False
    )

    async with session_factory() as session:
        restarted = await restart_submission(session, fake_state_service)
        await session.commit()

    assert restarted == 2
    assert await _status(session_factory, submit_interrupted) == (
        ProcessingState.LETTER_QUEUED
    )
    assert await _status(session_factory, submit_error) == (
        ProcessingState.LETTER_QUEUED
    )
    assert await _status(session_factory, gen_interrupted) == (
        ProcessingState.INTERRUPTED
    )


async def test_restart_submission_does_nothing_when_auto_submit_off(
    session_factory: async_sessionmaker[AsyncSession],
    fake_state_service: StateTransitionService,
) -> None:
    await _set_flags(session_factory, auto_generate=True, auto_submit=False)
    app_id = await _seed(
        session_factory, "l1", ProcessingState.INTERRUPTED, with_letter=True
    )

    async with session_factory() as session:
        restarted = await restart_submission(session, fake_state_service)
        await session.commit()

    assert restarted == 0
    assert await _status(session_factory, app_id) == ProcessingState.INTERRUPTED


async def test_restart_counts_split_by_phase(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed(session_factory, "l1", ProcessingState.INTERRUPTED, with_letter=False)
    await _seed(
        session_factory, "l2", ProcessingState.ERROR, error_domain=ErrorDomain.MODEL
    )
    await _seed(session_factory, "l3", ProcessingState.INTERRUPTED, with_letter=True)
    await _seed(
        session_factory,
        "l4",
        ProcessingState.ERROR,
        error_domain=ErrorDomain.SUBMISSION,
    )

    async with session_factory() as session:
        generation, submission = await restart_counts(session)

    assert generation == 2
    assert submission == 2
