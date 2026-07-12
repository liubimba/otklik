from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.models import ApplicationORM
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.state_machine import (
    ApplicationEvent,
    ProcessingStateMachine,
)

logger = get_logger(__name__)

# Состояния, в которых мяч на стороне пользователя: письмо готово и ждёт
# решения, письмо открыто на ревью, или обработка упала. LETTER_PENDING и
# LETTER_SENDING сюда не входят — там работает система, а не человек.
#
# Совпадает значениями с CHAT_EDITABLE_STATES (orchestrator/letter_chat_service.py),
# но это разные вопросы: там — «письмо можно править через AI-чат», здесь — «нужно
# решение пользователя». Совпадение случайное и временное: captcha-пауза (задача 2.5)
# требует действий пользователя, но чата в ней нет. Списки намеренно не объединены —
# менять их следует независимо.
NEEDS_ATTENTION_STATES: tuple[ProcessingState, ...] = (
    ProcessingState.LETTER_READY,
    ProcessingState.LETTER_REVIEWING,
    ProcessingState.ERROR,
)


class ApplicationRepository:
    @classmethod
    async def create(cls, session: AsyncSession, vacancy_id: int) -> ApplicationORM:
        logger.info(f"Create new application for vacancy id: {vacancy_id}")
        application = ApplicationORM(
            vacancy_id=vacancy_id, status=ProcessingState.PARSED
        )
        session.add(application)
        await session.commit()
        return application

    @classmethod
    async def get_by_id(
        cls, session: AsyncSession, application_id: int
    ) -> ApplicationORM | None:
        return await session.get(ApplicationORM, application_id)

    @classmethod
    async def get_by_vacancy_id(
        cls, session: AsyncSession, vacancy_id: int
    ) -> ApplicationORM | None:
        result = await session.execute(
            select(ApplicationORM)
            .where(ApplicationORM.vacancy_id == vacancy_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def transition(
        cls,
        session: AsyncSession,
        application_id: int,
        to_state: ApplicationEvent,
        error_message: str | None = None,
    ) -> ApplicationORM | None:
        application = await cls.get_by_id(
            session=session, application_id=application_id
        )
        if application is None:
            return None
        state_machine = ProcessingStateMachine(start_value=application.status)
        state_machine.send(to_state.value)
        application.status = ProcessingState(state_machine.current_state_value)
        application.error_message = error_message
        await session.commit()
        logger.info(
            "Transited application state",
            application_id=application_id,
            to_state=to_state,
        )
        return application

    @classmethod
    async def list_all(cls, session: AsyncSession) -> Sequence[ApplicationORM]:
        result = await session.execute(
            select(ApplicationORM).order_by(
                ApplicationORM.updated_at.desc().nulls_last(),
                ApplicationORM.created_at.desc(),
            )
        )
        return result.scalars().all()

    @classmethod
    async def list_active(cls, session: AsyncSession) -> Sequence[ApplicationORM]:
        result = await session.execute(
            select(ApplicationORM).where(
                ApplicationORM.status.not_in(
                    [ProcessingState.SKIPPED, ProcessingState.LETTER_SENT]
                )
            )
        )
        return result.scalars().all()

    @classmethod
    async def list_by_status(
        cls, session: AsyncSession, status: ProcessingState
    ) -> Sequence[ApplicationORM]:
        result = await session.execute(
            select(ApplicationORM).where(ApplicationORM.status == status)
        )
        return result.scalars().all()

    @classmethod
    async def count_needs_attention(cls, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count())
            .select_from(ApplicationORM)
            .where(ApplicationORM.status.in_(NEEDS_ATTENTION_STATES))
        )
        return int(result.scalar_one())
