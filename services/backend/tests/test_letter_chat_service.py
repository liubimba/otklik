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

    payload = (
        '{"reply": "Добавил больше деталей про ваш опыт.", '
        f'"letter": "{REVISED_LETTER}"}}'
    )
    chunks = [payload[i : i + 7] for i in range(0, len(payload), 7)]

    events = await _run(session_factory, chunks)

    letter_events = [e for e in events if e["type"] == "letter"]
    reply_events = [e for e in events if e["type"] == "reply"]
    assert letter_events, "revised letter must stream on the letter channel"
    reply_text = "".join(str(e["delta"]) for e in reply_events)
    assert REVISED_LETTER not in reply_text, "letter must not leak into the reply"

    done = next(e for e in events if e["type"] == "done")
    assert done["version"] is not None, "a revision must create a new letter version"

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
    await _seed_error(session_factory)

    payload = (
        '{"reply": "Поправил письмо после ошибки.", ' f'"letter": "{REVISED_LETTER}"}}'
    )
    chunks = [payload[i : i + 7] for i in range(0, len(payload), 7)]

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
        assert latest is not None and latest.version == 1


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
        assert latest is not None and latest.version == 1


async def test_signature_the_user_asked_for_is_preserved(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_letter_ready(session_factory)

    body = (
        "Уважаемый работодатель, я внимательно изучил вашу вакансию и хочу "
        "поделиться, почему эта позиция мне подходит: за последние три года "
        "я разрабатывал похожие системы и готов приступить к работе "
        "немедленно."
    )
    signature = "С уважением, Иван Петров"
    signed_letter = body + "\n" + signature
    payload = (
        '{"reply": "Добавил подпись.", "letter": "' + body + "\\n" + signature + '"}'
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
        assert latest is not None and latest.version == 1
