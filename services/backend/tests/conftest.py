from fastapi.testclient import TestClient
from headhunter_backend.log import configure_logging
from headhunter_backend.domain.enums import WorkFormat, EmploymentType
from headhunter_backend.api.app import app
from headhunter_backend.api.dependencies import (
    get_broadcaster,
    get_browser,
    get_session,
)
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import AuthStatus
from headhunter_backend.db.base import Base
from headhunter_backend.orchestrator.queue import Orchestrator
from headhunter_backend.db.converters import vacancy_to_orm
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
    create_async_engine,
)
from pathlib import Path
import pytest
from headhunter_backend.domain.models import VacancyModel
from headhunter_backend.db.session import apply_sqlite_pragmas
from headhunter_backend.db.crud import create_vacancy

configure_logging()


class FakeBrowser:
    def __init__(self):
        self._authenticated = AuthStatus.unauthorized()

    async def get_auth_status(self) -> AuthStatus:
        return self._authenticated

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        self._authenticated = AuthStatus.authorized()


@pytest.fixture
def fake_broadcaster() -> EventBroadcaster:
    return EventBroadcaster()


@pytest.fixture
def fake_browser() -> FakeBrowser:
    return FakeBrowser()


@pytest.fixture
async def session_factory(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine: AsyncEngine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / "test.sqlite"}"
    )
    apply_sqlite_pragmas(target_engine=engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
async def client(
    fake_browser: FakeBrowser,
    fake_broadcaster: EventBroadcaster,
    vacancy_model: VacancyModel,
    session_factory: async_sessionmaker[AsyncSession],
) -> TestClient:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_browser] = lambda: fake_browser
    app.dependency_overrides[get_broadcaster] = lambda: fake_broadcaster

    async with session_factory() as session:
        await create_vacancy(session=session, vacancy=vacancy_to_orm(vacancy_model))

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def fake_orchestrator() -> Orchestrator:
    return Orchestrator()


@pytest.fixture
def vacancy_model() -> VacancyModel:
    return VacancyModel(
        title="Python Developer",
        apply_link="https://hh.ru/vacancy/12345",
        description="Build and ship backend services.",
        company_name="ACME",
        salary="200000 RUB",
        work_formats=[WorkFormat.REMOTE, WorkFormat.HYBRID],
        employment_types=[EmploymentType.FULL_TIME, EmploymentType.PART_TIME],
        work_experience="1-3 years",
    )
