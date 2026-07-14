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

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.models import ApplicationORM, VacancyORM
from otklik_backend.db.repositories.chat_messages import ChatMessageRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.orchestrator.letter_chat_service import LetterChatService

REVISED_LETTER = (
    "Уважаемый работодатель, вот значительно расширенное письмо с деталями."
)


class _FakeAILayer:
    """Emits a fixed sequence of streamed content chunks."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

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


async def test_signature_the_user_asked_for_is_preserved(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Regression: LetterCleaner used to run on the chat path too, so a
    # signature the user explicitly asked for ("добавь подпись: С уважением,
    # Иван Петров") got written by the model and immediately cut back out by
    # the cleaner — the saved letter matched the old one, no new version was
    # created, and the reply claimed "added the signature" over an unchanged
    # letter with no way to escape the loop. Chat is a human-in-the-loop
    # surface — the user drives the text and sees the result, so nothing
    # auto-cleans it. Cleaning stays on the unattended first-generation path
    # only (AILayer.generate_cover_letter).
    await _seed_letter_ready(session_factory)

    signature = "С уважением, Иван Петров"
    signed_letter = REVISED_LETTER + "\n" + signature
    payload = (
        '{"reply": "Добавил подпись.", "letter": "'
        + REVISED_LETTER
        + "\\n"
        + signature
        + '"}'
    )
    chunks = [payload[i : i + 9] for i in range(0, len(payload), 9)]

    events = await _run(session_factory, chunks, message=f"Добавь подпись: {signature}")

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is not None, "signed letter differs — must create a version"

    async with session_factory() as session:
        latest = await CoverLetterRepository.get_latest_by_application_id(
            session=session, application_id=1
        )
        assert latest is not None
        assert latest.version == 2
        assert latest.text == signed_letter
        assert signature in latest.text


async def test_echoed_letter_with_trailing_newline_does_not_create_a_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Regression: without the caller's own .strip() on the parsed letter, a
    # trailing newline the model echoes back would look different from
    # `current_letter.strip()` below and spawn a spurious version — chat has
    # no cleaner to normalise it away (see
    # test_signature_the_user_asked_for_is_preserved).
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
