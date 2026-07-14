import re
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from otklik_backend.ai.layer import AILayer
from otklik_backend.ai.postprocess import LetterCleaner
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

# Chat is a content operation on an existing letter, available while the letter
# is up for review (LETTER_READY / LETTER_REVIEWING) and in ERROR — a failed
# letter is still fixable by asking the AI, matching the actionable-error set the
# UI uses for submit/regenerate/save (canChat in the viewmodel must stay in sync).
# Not allowed mid-regenerate (LETTER_PENDING), while sending, or once terminal.
#
# Value-identical to NEEDS_ATTENTION_STATES (db/repositories/applications.py) today,
# but the two answer different questions — "can the AI edit this letter?" versus
# "does the user owe a decision?" — and will diverge at the captcha pause (task 2.5),
# which needs the user but offers no chat. Deliberately NOT merged; change each on
# its own merits.
CHAT_EDITABLE_STATES = frozenset(
    {
        ProcessingState.LETTER_READY,
        ProcessingState.LETTER_REVIEWING,
        ProcessingState.ERROR,
    }
)


class StreamingJsonChatParser:
    """Incrementally parses the model's streamed JSON object `{reply, letter}`
    and yields decoded deltas per field.

    The model can't leak the letter into the reply, because each lives in its
    own field (the delimiter approach could — the model sometimes dropped the
    marker and the whole revision fell into the reply). `letter` may be a JSON
    string (a revision) or `null`/absent (a pure answer); `has_letter` reports
    which. The full accumulated buffer is re-scanned each feed — cheap for
    chat-sized text — locating each field's value and emitting only newly
    decoded characters, so a JSON escape or the closing quote never straddles a
    chunk boundary.
    """

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
        """Decode a JSON string body from `start` (just past the opening quote)
        up to the closing unescaped quote. Returns (decoded, close_index) or
        (decoded_so_far, None) when the value is still partial — stopping before
        any incomplete trailing escape so it is never emitted half-decoded.
        """
        out: list[str] = []
        i, n = start, len(s)
        while i < n:
            c = s[i]
            if c == '"':
                return "".join(out), i
            if c == "\\":
                if i + 1 >= n:
                    break  # dangling backslash — wait for more input
                nxt = s[i + 1]
                if nxt == "u":
                    if i + 6 > n:
                        break  # incomplete \uXXXX
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
    """Runs one turn of the letter-editing conversation as a stream of typed
    events. Persists the user message up front, streams the model's response
    split into reply/letter channels, then persists the assistant message and
    (if the letter changed) a new cover-letter version tagged `source="chat"`.
    """

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        ai_layer: AILayer,
    ) -> None:
        self._session_maker = session_maker
        self._ai_layer = ai_layer
        self._cleaner = LetterCleaner()
        self._log = get_logger(__name__)

    async def stream_turn(
        self, vacancy_id: int, message: str
    ) -> AsyncIterator[dict[str, object]]:
        # 1. Load context + guard + persist the user turn (short-lived session).
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

        # 2. Stream the model, parsing reply vs. letter from its JSON response
        #    (no DB session held).
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

        # 3. Persist the assistant turn + (if changed) a new letter version.
        #    Only version an ACTUAL change — the model sometimes echoes the
        #    unchanged letter while answering a question; that must not spawn a
        #    spurious version.
        reply = parser.reply.strip()
        # Чистим тут, а не по токенам стрима: чистка по кускам порезала бы
        # текст на границе чанка (регулярка увидела бы половину строки).
        # Пользователю в стрим летят сырые токены, а в базу и в результат —
        # уже собранное и очищенное письмо.
        # .strip() тут, а не в LetterCleaner: предохранитель чистильщика
        # осознанно возвращает исходный текст как есть при коротких письмах
        # (см. test_returns_original_when_cleaning_would_gut_the_letter), а
        # нестрипнутый хвост из этой ветки иначе даёт ложное "письмо
        # изменилось" при сравнении с current_letter.strip() ниже.
        letter_text = (
            self._cleaner.clean(parser.letter).strip() if parser.letter else ""
        )
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
