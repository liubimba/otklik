import re
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.ai.layer import AILayer
from otklik_backend.api.schemas import ProcessingState
from otklik_backend.db.converters import vacancy_to_schema
from otklik_backend.db.models import ApplicationORM, SettingsORM, VacancyORM
from otklik_backend.db.repositories.applications import ApplicationRepository
from otklik_backend.db.repositories.chat_messages import ChatMessageRepository
from otklik_backend.db.repositories.cover_letters import CoverLetterRepository
from otklik_backend.db.repositories.settings import SettingsRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository
from otklik_backend.exceptions import ApplicationNotFoundError, VacancyNotFoundError
from otklik_backend.log import get_logger
from otklik_backend.orchestrator.exceptions import LetterChatNotAllowedError

CHAT_EDITABLE_STATES = frozenset(
    {
        ProcessingState.LETTER_READY,
        ProcessingState.LETTER_REVIEWING,
        ProcessingState.ERROR,
    }
)


class StreamingJsonChatParser:
    def __init__(self) -> None:
        self._raw = ""
        self.reply = ""
        self.letter = ""
        self.has_letter = False
        self._reply_emitted = 0
        self._letter_emitted = 0

    def feed(self, delta: str) -> list[tuple[str, str]]:
        self._raw += delta
        events: list[tuple[str, str]] = []
        self._pump("reply", events)
        if re.search(r'"letter"\s*:\s*null', self._raw):
            self.has_letter = False
        else:
            self._pump("letter", events)
        return events

    def finish(self) -> list[tuple[str, str]]:
        return []

    def _pump(self, field: str, events: list[tuple[str, str]]) -> None:
        match = re.search(rf'"{field}"\s*:\s*"', self._raw)
        if match is None:
            return
        if field == "letter":
            self.has_letter = True
        body, _ = self._decode_string(self._raw, match.end())
        emitted = self._reply_emitted if field == "reply" else self._letter_emitted
        if len(body) <= emitted:
            return
        new = body[emitted:]
        if field == "reply":
            self.reply += new
            self._reply_emitted += len(new)
        else:
            self.letter += new
            self._letter_emitted += len(new)
        events.append((field, new))

    _ESCAPES = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def _decode_string(self, s: str, start: int) -> tuple[str, int | None]:
        out: list[str] = []
        i, n = start, len(s)
        while i < n:
            c = s[i]
            if c == '"':
                return "".join(out), i
            if c == "\\":
                if i + 1 >= n:
                    break
                nxt = s[i + 1]
                if nxt == "u":
                    if i + 6 > n:
                        break
                    out.append(chr(int(s[i + 2 : i + 6], 16)))
                    i += 6
                    continue
                out.append(self._ESCAPES.get(nxt, nxt))
                i += 2
                continue
            out.append(c)
            i += 1
        return "".join(out), None


class LetterChatService:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        ai_layer: AILayer,
    ) -> None:
        self._session_maker = session_maker
        self._ai_layer = ai_layer
        self._log = get_logger(__name__)

    async def stream_turn(
        self, vacancy_id: int, message: str
    ) -> AsyncIterator[dict[str, object]]:
        async with self._session_maker() as session:
            vacancy_orm: VacancyORM | None = await VacancyRepository.get_by_id(
                session=session, vacancy_id=vacancy_id
            )
            if vacancy_orm is None:
                raise VacancyNotFoundError()
            application: (
                ApplicationORM | None
            ) = await ApplicationRepository.get_by_vacancy_id(
                session=session, vacancy_id=vacancy_id
            )
            if application is None:
                raise ApplicationNotFoundError()
            if application.status not in CHAT_EDITABLE_STATES:
                raise LetterChatNotAllowedError()

            application_id = application.id
            settings: SettingsORM = await SettingsRepository.get(session=session)
            resume = settings.resume_text
            style = settings.letter_style
            latest = await CoverLetterRepository.get_latest_by_application_id(
                session=session, application_id=application_id
            )
            current_letter = latest.text if latest is not None else ""
            history = [
                (m.role, m.content)
                for m in await ChatMessageRepository.list_by_application_id(
                    session=session, application_id=application_id
                )
            ]
            vacancy_schema = vacancy_to_schema(vacancy_orm)
            await ChatMessageRepository.create(
                session=session,
                application_id=application_id,
                role="user",
                content=message,
            )

        parser = StreamingJsonChatParser()
        async for delta in self._ai_layer.stream_letter_chat(
            vacancy_model=vacancy_schema,
            resume=resume,
            style=style,
            current_letter=current_letter,
            history=history,
            user_message=message,
        ):
            for channel, text in parser.feed(delta):
                yield {"type": channel, "delta": text}
        for channel, text in parser.finish():
            yield {"type": channel, "delta": text}

        reply = parser.reply.strip()
        letter_text = parser.letter.strip() if parser.letter else ""
        letter = (
            letter_text
            if parser.has_letter
            and letter_text
            and letter_text != current_letter.strip()
            else None
        )
        produced_version: int | None = None
        async with self._session_maker() as session:
            if letter:
                created = await CoverLetterRepository.create(
                    session=session,
                    application_id=application_id,
                    text=letter,
                    source="chat",
                )
                produced_version = created.version
            await ChatMessageRepository.create(
                session=session,
                application_id=application_id,
                role="assistant",
                content=reply,
                produced_version=produced_version,
            )
        yield {"type": "done", "version": produced_version}
