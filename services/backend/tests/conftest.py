from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from headhunter_backend.log import configure_logging
from headhunter_backend.api.schemas import WorkFormat, EmploymentType
from headhunter_backend.api.app import app
from headhunter_backend.api.dependencies import (
    get_ai_layer,
    get_authorization_service,
    get_broadcaster,
    get_browser,
    get_cover_letter_service,
    get_session,
    get_orchestrator,
    get_state_service,
    get_writer,
    get_search_service,
)
from headhunter_backend.api.broadcaster import EventBroadcaster
from headhunter_backend.api.schemas import AuthStatusAPISchema
from headhunter_backend.db.base import Base
from headhunter_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from headhunter_backend.orchestrator.state_service import StateTransitionService
from headhunter_backend.db.converters import vacancy_to_orm
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
    create_async_engine,
)
from pydantic import BaseModel
from pathlib import Path
import pytest
import uuid
import asyncio
from headhunter_backend.api.schemas import VacancyAPISchema
from headhunter_backend.db.session import apply_sqlite_pragmas
from headhunter_backend.core.site.result import SubmissionResult
from headhunter_backend.orchestrator.search import (
    SearchAlreadyRunningError,
    SearchSessionTask,
)
from headhunter_backend.api.schemas import VacanciesStartSearchRequestAPISchema
from headhunter_backend.ai.deployment import LLMDeployment
from headhunter_backend.ai.layer import AILayer
from headhunter_backend.db.repositories.vacancies import VacancyRepository

configure_logging()


async def wait_until(predicate, timeout: float = 2.0, interval: float = 0.02) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if await predicate() if asyncio.iscoroutinefunction(predicate) else predicate():
            return
        await asyncio.sleep(interval)
    raise TimeoutError("Condition not met within timeout")


class RecordingBroadcaster(EventBroadcaster):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[BaseModel] = []

    async def publish(self, event: BaseModel) -> None:
        self.events.append(event)
        await super().publish(event=event)


class FakeBrowser:
    """Dual-purpose fake: implements the SiteAuthFlow protocol (so tests can
    inject it as `auth_flow`) while also being a stand-in for a BrowserCore
    handle. The real code has these split — the test seam does not need to."""

    def __init__(self) -> None:
        self._authenticated = AuthStatusAPISchema.unauthorized()

    async def get_auth_status(self) -> AuthStatusAPISchema:
        return self._authenticated

    async def wait_for_login(self, poll_interval: float = 1.0) -> None:
        self._authenticated = AuthStatusAPISchema.authorized()

    async def unauthorize(self) -> None:
        self._authenticated = AuthStatusAPISchema.unauthorized()


class FakeSearchService:
    def __init__(self) -> None:
        self._queue: dict[str, SearchSessionTask] = {}

    async def open_search_session(
        self, request: VacanciesStartSearchRequestAPISchema
    ) -> SearchSessionTask:
        if len(self._queue) > 0:
            raise SearchAlreadyRunningError()
        search_id: str = str(uuid.uuid4())
        task = SearchSessionTask(id=search_id, task=None)  # type: ignore[arg-type]
        self._queue[search_id] = task
        return task

    async def cancel_search_session(self, search_id: str) -> bool:
        if search_id in self._queue:
            del self._queue[search_id]
            return True
        return False

    def find_search_task(self, search_id: str) -> SearchSessionTask | None:
        return self._queue.get(search_id)

    def get_current_search_task(self) -> SearchSessionTask | None:
        for task in self._queue.values():
            return task
        return None

    async def shutdown(self) -> None:
        self._queue.clear()


class FakeWriter:
    def __init__(self, results: list[SubmissionResult] | None = None) -> None:
        self._results: list[SubmissionResult] = list(results) if results else []
        self.calls: list[dict[str, str]] = []
        self.invoked: asyncio.Event = asyncio.Event()

    def queue(self, *results: SubmissionResult) -> None:
        self._results.extend(results)

    async def submit(self, vacancy_url: str, letter_text: str) -> SubmissionResult:
        self.calls.append({"uri": vacancy_url, "text": letter_text})
        self.invoked.set()
        if self._results:
            return self._results.pop(0)
        return SubmissionResult.submitted()


@pytest.fixture
def authenticated_browser(fake_browser: FakeBrowser) -> FakeBrowser:
    fake_browser._authenticated = AuthStatusAPISchema.authorized()
    return fake_browser


@pytest.fixture
def recording_broadcaster() -> RecordingBroadcaster:
    return RecordingBroadcaster()


@pytest.fixture
def fake_state_service(
    recording_broadcaster: RecordingBroadcaster,
) -> StateTransitionService:
    return StateTransitionService(broadcaster=recording_broadcaster)


@pytest.fixture
def fake_orchestrator(
    fake_state_service: StateTransitionService,
    fake_browser: "FakeBrowser",
    fake_writer: "FakeWriter",
    recording_broadcaster: RecordingBroadcaster,
    session_factory: async_sessionmaker[AsyncSession],
) -> LetterSendingWorker:
    return LetterSendingWorker(
        state_service=fake_state_service,
        session_maker=session_factory,
        auth_flow=fake_browser,  # type: ignore[arg-type]
        writer=fake_writer,  # type: ignore[arg-type]
        broadcaster=recording_broadcaster,
        rate_limit_backoff_sec=0.05,
    )


@pytest.fixture
def fake_browser() -> FakeBrowser:
    return FakeBrowser()


@pytest.fixture
def fake_writer() -> FakeWriter:
    return FakeWriter()


@pytest.fixture
def fake_search_service() -> FakeSearchService:
    return FakeSearchService()


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
def make_ai_layer():
    def _make(deployments: list[LLMDeployment] | None = None) -> AILayer:
        layer: AILayer = AILayer(deployments=deployments or [])
        layer._router = AsyncMock()
        return layer

    return _make


@pytest.fixture
def ai_layer_with_router(make_ai_layer) -> AILayer:
    return make_ai_layer(
        [LLMDeployment(model="groq/llama-3.3-70b-versatile", api_key="test-key")]
    )


@pytest.fixture
async def client(
    fake_browser: FakeBrowser,
    recording_broadcaster: RecordingBroadcaster,
    fake_orchestrator: LetterSendingWorker,
    fake_state_service: StateTransitionService,
    fake_writer: FakeWriter,
    vacancy_model: VacancyAPISchema,
    session_factory: async_sessionmaker[AsyncSession],
    fake_search_service: FakeSearchService,
    ai_layer_with_router: AILayer,
) -> TestClient:
    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    from headhunter_backend.orchestrator.authorization_service import (
        AuthorizationService,
    )
    from headhunter_backend.orchestrator.cover_letter_service import CoverLetterService

    authorization_service = AuthorizationService(
        broadcaster=recording_broadcaster, auth_flow=fake_browser
    )
    cover_letter_service = CoverLetterService(
        session_maker=session_factory,
        ai_layer=ai_layer_with_router,
        state_service=fake_state_service,
    )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_browser] = lambda: fake_browser
    app.dependency_overrides[get_broadcaster] = lambda: recording_broadcaster
    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    app.dependency_overrides[get_state_service] = lambda: fake_state_service
    app.dependency_overrides[get_writer] = lambda: fake_writer
    app.dependency_overrides[get_search_service] = lambda: fake_search_service
    app.dependency_overrides[get_ai_layer] = lambda: ai_layer_with_router
    app.dependency_overrides[get_authorization_service] = lambda: authorization_service
    app.dependency_overrides[get_cover_letter_service] = lambda: cover_letter_service

    async with session_factory() as session:
        await VacancyRepository.create(
            session=session, vacancy=vacancy_to_orm(vacancy_model)
        )

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def vacancy_model() -> VacancyAPISchema:
    return VacancyAPISchema(
        title="Python Developer",
        apply_link="https://hh.ru/vacancy/12345",
        description="Build and ship backend services.",
        company_name="ACME",
        salary="200000 RUB",
        work_formats=[WorkFormat.REMOTE, WorkFormat.HYBRID],
        employment_types=[EmploymentType.FULL_TIME, EmploymentType.PART_TIME],
        work_experience="1-3 years",
    )
