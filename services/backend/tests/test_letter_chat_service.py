"""Regression for the "revised letter leaks into the chat reply" bug.

Reported 2026-07-06: while chatting, the user asked the AI to edit the letter;
the AI answered in chat with a whole new letter ("вот обновлённое письмо…") but
the editor's letter never changed and no new version was stored. Root cause: the
letter/reply split depended on the model emitting an exact `<<<LETTER>>>` marker,
and when it drifted and omitted the marker, the entire revision fell into the
reply channel — so `saw_marker` was False and no version was created.

The fix makes the model return a structured object `{reply, letter}`; the letter
lives in its own field and cannot leak into the reply. These tests feed the
service that structured stream and assert the revision is applied.
"""

import json
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.ai.health import AILayerHealthStatus
from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.models import ApplicationORM, VacancyORM
from otklik_backend.db.repositories.chat_messages import ChatMessageRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.orchestrator.letter_chat_service import LetterChatService

REVISED_LETTER = (
    "Уважаемый работодатель, вот значительно расширенное письмо с деталями."
)

# Long enough that LetterCleaner actually cleans it instead of tripping its
# gut-guard (MIN_LETTER_CHARS) and returning the input untouched — the other
# fixtures in this file are all short letters, which never exercises the
# cleaner's real cleaning path, only its fallback.
LONG_LETTER_BODY = (
    "Уважаемый работодатель, хочу присоединиться к вашей команде и принести "
    "пользу проекту. Мой опыт разработки бэкенда и внимание к деталям помогут "
    "закрыть эту вакансию быстро и качественно."
)
LONG_LETTER_WITH_SIGNATURE = LONG_LETTER_BODY + "\nС уважением,\n[Ваше имя]"


class _FakeAILayer:
    """Emits a fixed sequence of streamed content chunks."""

    def __init__(self, chunks: list[str], healthy: bool = True) -> None:
        self._chunks = chunks
        self._healthy = healthy

    async def get_health_status(self) -> AILayerHealthStatus:
        return (
            AILayerHealthStatus.HEALTHY
            if self._healthy
            else AILayerHealthStatus.UNHEALTHY
        )

    async def stream_letter_chat(self, **_: object) -> AsyncIterator[str]:
        for chunk in self._chunks:
            yield chunk


async def _seed_letter_ready(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(
            VacancyORM(
                id=1,
                title="Менеджер",
                apply_link="https://hh.ru/vacancy/1",
                description="Описание вакансии",
                work_formats=[],
                employment_types=[],
            )
        )
        await session.commit()
        session.add(
            ApplicationORM(id=1, vacancy_id=1, status=ProcessingState.LETTER_READY)
        )
        await session.commit()
        await CoverLetterRepository.create(
            session=session, application_id=1, text="Старое письмо", source="generated"
        )


async def _seed_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(
            VacancyORM(
                id=1,
                title="Менеджер",
                apply_link="https://hh.ru/vacancy/1",
                description="Описание вакансии",
                work_formats=[],
                employment_types=[],
            )
        )
        await session.commit()
        session.add(ApplicationORM(id=1, vacancy_id=1, status=ProcessingState.ERROR))
        await session.commit()
        await CoverLetterRepository.create(
            session=session, application_id=1, text="Старое письмо", source="generated"
        )


async def _run(
    session_factory: async_sessionmaker[AsyncSession],
    chunks: list[str],
    message: str = "Добавь больше деталей про мой опыт.",
) -> list[dict[str, object]]:
    service = LetterChatService(
        session_maker=session_factory,
        ai_layer=_FakeAILayer(chunks),  # type: ignore[arg-type]
    )
    return [event async for event in service.stream_turn(1, message)]


async def test_revision_is_applied_not_leaked_into_reply(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_letter_ready(session_factory)

    # The model's structured revision, streamed across chunk boundaries.
    payload = (
        '{"reply": "Добавил больше деталей про ваш опыт.", '
        f'"letter": "{REVISED_LETTER}"}}'
    )
    chunks = [payload[i : i + 7] for i in range(0, len(payload), 7)]

    events = await _run(session_factory, chunks)

    # The revised letter streamed to the editor, not the chat.
    letter_events = [e for e in events if e["type"] == "letter"]
    reply_events = [e for e in events if e["type"] == "reply"]
    assert letter_events, "revised letter must stream on the letter channel"
    reply_text = "".join(str(e["delta"]) for e in reply_events)
    assert REVISED_LETTER not in reply_text, "letter must not leak into the reply"

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is not None, "a revision must create a new letter version"

    # Persisted: a new chat-sourced version + assistant message linked to it.
    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None
        assert latest.version == 2
        assert latest.source == "chat"
        assert latest.text.strip() == REVISED_LETTER
        messages = await ChatMessageRepository.list_by_application_id(
            session=session, application_id=1
        )
        assistant = [m for m in messages if m.role == "assistant"][-1]
        assert assistant.produced_version == 2
        assert REVISED_LETTER not in assistant.content


async def test_chat_allowed_in_error_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Regression: ERROR was made actionable (submit/regenerate/save) but chat
    # stayed blocked — CHAT_EDITABLE_STATES excluded ERROR, so stream_turn
    # raised LetterChatNotAllowedError. A user with a failed letter must be
    # able to ask the AI to fix it.
    await _seed_error(session_factory)

    payload = (
        '{"reply": "Поправил письмо после ошибки.", ' f'"letter": "{REVISED_LETTER}"}}'
    )
    chunks = [payload[i : i + 7] for i in range(0, len(payload), 7)]

    # Must not raise LetterChatNotAllowedError while iterating.
    events = await _run(session_factory, chunks)

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is not None, "chat in ERROR must produce a revision"
    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None
        assert latest.version == 2
        assert latest.source == "chat"


async def test_echoed_unchanged_letter_does_not_create_a_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Answering a question, the model sometimes re-emits the current letter
    # verbatim in the `letter` field — that must not spawn a spurious version.
    await _seed_letter_ready(session_factory)
    payload = '{"reply": "Подчеркнул ваши навыки.", "letter": "Старое письмо"}'
    chunks = [payload[i : i + 6] for i in range(0, len(payload), 6)]
    events = await _run(session_factory, chunks, message="Что ты подчеркнул?")

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is None
    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None and latest.version == 1  # unchanged


async def test_question_produces_reply_only_no_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_letter_ready(session_factory)

    payload = '{"reply": "Я выбрал формальный тон под эту вакансию.", "letter": null}'
    chunks = [payload[i : i + 5] for i in range(0, len(payload), 5)]

    events = await _run(session_factory, chunks, message="Почему такой тон?")

    assert [e for e in events if e["type"] == "letter"] == []
    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is None

    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None and latest.version == 1  # unchanged


async def test_signature_and_placeholder_are_stripped_from_saved_letter(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # LetterCleaner is wired into the chat path, but every other fixture here
    # is short enough to hit its gut-guard and skip cleaning entirely. Use a
    # long revision so the signature and `[Ваше имя]` placeholder are actually
    # cut — proving the cleaner runs, not just that it's a no-op.
    await _seed_letter_ready(session_factory)

    payload = (
        '{"reply": "Убрал подпись, как договорились.", "letter": '
        f"{json.dumps(LONG_LETTER_WITH_SIGNATURE)}}}"
    )
    chunks = [payload[i : i + 11] for i in range(0, len(payload), 11)]

    events = await _run(session_factory, chunks, message="Убери подпись.")

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is not None

    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None
        assert latest.version == 2
        assert latest.text == LONG_LETTER_BODY
        assert "С уважением" not in latest.text
        assert "[" not in latest.text and "]" not in latest.text


async def test_echoed_letter_with_trailing_newline_does_not_create_a_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Regression: the letter/reply channel is cleaned with
    # `self._cleaner.clean(...)`, whose gut-guard returns the input verbatim
    # (unstripped) for short letters — which is every letter in this test
    # file. If the caller doesn't strip that result before comparing it to
    # `current_letter.strip()`, a trailing newline the model echoes back
    # looks like a real edit and spawns a spurious version.
    await _seed_letter_ready(session_factory)
    payload = '{"reply": "Ничего не меняю.", "letter": "Старое письмо\\n"}'
    chunks = [payload[i : i + 6] for i in range(0, len(payload), 6)]
    events = await _run(session_factory, chunks, message="Всё ок?")

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is None

    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None and latest.version == 1  # unchanged
