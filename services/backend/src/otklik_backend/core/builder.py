from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.ai.layer import AILayer
from otklik_backend.api.broadcaster import EventBroadcaster
from otklik_backend.browser.core import BrowserCore
from otklik_backend.core.protocols import EventListener, Recoverable, Runnable
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.authorization_service import AuthorizationService
from otklik_backend.orchestrator.cover_letter_service import CoverLetterService
from otklik_backend.orchestrator.letter_chat_service import LetterChatService
from otklik_backend.orchestrator.listeners.auto_apply import AutoApplyListener
from otklik_backend.orchestrator.listeners.auto_submit import AutoSubmitListener
from otklik_backend.orchestrator.search import SearchService
from otklik_backend.orchestrator.state_service import StateTransitionService
from otklik_backend.orchestrator.workers.letter_pending import LetterPendingWorker
from otklik_backend.orchestrator.workers.letter_sending import LetterSendingWorker
from otklik_backend.sites.hh_ru import HHRUAuthFlow, HHRUParser, HHRUWriter

logger = get_logger(__name__)


@dataclass(frozen=True)
class AppContext:
    browser: BrowserCore
    auth_flow: HHRUAuthFlow
    broadcaster: EventBroadcaster
    state_service: StateTransitionService
    writer: HHRUWriter
    search_service: SearchService
    ai_layer: AILayer
    cover_letter_service: CoverLetterService
    letter_chat_service: LetterChatService
    letter_sending_worker: LetterSendingWorker
    letter_pending_worker: LetterPendingWorker
    auto_submit_listener: AutoSubmitListener
    auto_apply_listener: AutoApplyListener
    authorization_service: AuthorizationService

    def runnables(self) -> list[Runnable]:
        return [self.letter_sending_worker, self.letter_pending_worker]

    def recoverables(self) -> list[Recoverable]:
        return [
            self.letter_sending_worker,
            self.letter_pending_worker,
            self.auto_submit_listener,
        ]

    def event_listeners(self) -> list[EventListener]:
        # Anything with .start()/.stop() that subscribes to the broadcaster.
        return [
            self.letter_sending_worker,
            self.letter_pending_worker,
            self.auto_submit_listener,
            self.auto_apply_listener,
        ]


class BackendBuilder:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def build(self) -> AppContext:
        browser = BrowserCore()
        auth_flow = HHRUAuthFlow(browser=browser)
        broadcaster = EventBroadcaster()
        state_service = StateTransitionService(broadcaster=broadcaster)
        writer = HHRUWriter(core=browser, min_delay_ms=800, jitter_delay_ms=400)
        search_service = SearchService(
            core=browser,
            parser=HHRUParser(core=browser),
            broadcaster=broadcaster,
            session_maker=self._session_maker,
        )
        letter_sending_worker = LetterSendingWorker(
            state_service=state_service,
            session_maker=self._session_maker,
            auth_flow=auth_flow,
            writer=writer,
            broadcaster=broadcaster,
        )
        ai_layer = await self._bootstrap_ai_layer()
        cover_letter_service = CoverLetterService(
            session_maker=self._session_maker,
            ai_layer=ai_layer,
            state_service=state_service,
        )
        letter_chat_service = LetterChatService(
            session_maker=self._session_maker,
            ai_layer=ai_layer,
        )
        letter_pending_worker = LetterPendingWorker(
            cover_letter_service=cover_letter_service,
            state_service=state_service,
            session_maker=self._session_maker,
            broadcaster=broadcaster,
        )
        auto_submit_listener = AutoSubmitListener(
            state_service=state_service,
            session_maker=self._session_maker,
            broadcaster=broadcaster,
            letter_sending_worker=letter_sending_worker,
        )
        auto_apply_listener = AutoApplyListener(
            session_maker=self._session_maker,
            state_service=state_service,
            broadcaster=broadcaster,
        )
        authorization_service = AuthorizationService(
            broadcaster=broadcaster, auth_flow=auth_flow
        )
        return AppContext(
            browser=browser,
            auth_flow=auth_flow,
            broadcaster=broadcaster,
            state_service=state_service,
            writer=writer,
            search_service=search_service,
            ai_layer=ai_layer,
            cover_letter_service=cover_letter_service,
            letter_chat_service=letter_chat_service,
            letter_sending_worker=letter_sending_worker,
            letter_pending_worker=letter_pending_worker,
            auto_submit_listener=auto_submit_listener,
            auto_apply_listener=auto_apply_listener,
            authorization_service=authorization_service,
        )

    async def _bootstrap_ai_layer(self) -> AILayer:
        async with self._session_maker() as session:
            settings: SettingsORM = await SettingsRepository.get(session=session)
        try:
            return AILayer(deployments=settings.llm_deployments)
        except Exception as e:
            logger.error(
                "Failed to initialize AI Layer with error: %s. Initializing with no deployments.",
                str(e),
            )
            return AILayer()
