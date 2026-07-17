"""Seed a DEMO database for landing-page screenshots.

Everything here is invented — no real resume, no real API keys, no real
companies the user applied to. See docs/screenshots-brief.md §4.

The script never touches the real database. It resolves its path through
`AppPaths`, which hangs off `Path.home()` — so run it with HOME pointed at a
throwaway directory:

    HOME=/tmp/otklik-demo uv run python scripts/seed_demo_db.py

and start the backend the same way. `~/.otklik/db.sqlite` is left alone.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from otklik_backend.ai.deployment import LLMDeployment
from otklik_backend.api.schemas import ProcessingState, SearchStatusAPISchema
from otklik_backend.db.base import Base
from otklik_backend.db.models import (
    ApplicationORM,
    ChatMessageORM,
    CoverLetterORM,
    SearchHistoryORM,
    SettingsORM,
    VacancyORM,
    search_vacancies_table,
)
from otklik_backend.paths import AppPaths

SEARCH_ID = "demo-search-0001"

RESUME = """Бэкенд-разработчик, 6 лет коммерческого опыта.

Python (FastAPI, SQLAlchemy, asyncio), PostgreSQL, Redis, Kafka. Docker,
Kubernetes, GitLab CI. Проектировал и вёл в проде сервисы с нагрузкой до
3000 RPS: биллинг, интеграции с внешними платёжными провайдерами,
асинхронные очереди обработки.

Последние два года — техлид команды из четырёх человек: код-ревью,
архитектурные решения, найм. Веду курс по асинхронному Python внутри
компании.

Ищу продуктовую команду, где инженер участвует в решениях, а не только
в их реализации. Открыт к удалёнке и гибриду."""

LETTER_STYLE = "Нейтрально, по делу, без канцелярита. До 250 слов, от первого лица."

SYSTEM_PROMPT = (
    "Ты пишешь сопроводительные письма от лица соискателя. Опирайся только на "
    "факты из резюме — ничего не выдумывай. Свяжи опыт кандидата с конкретными "
    "требованиями вакансии. Пиши по-русски, живо и коротко."
)

DEPLOYMENTS = [
    LLMDeployment(model="anthropic/claude-3-5-sonnet", has_api_key=True),
    LLMDeployment(model="openai/gpt-4o", has_api_key=True),
    LLMDeployment(model="ollama/llama3", api_base="http://localhost:11434"),
]

# (title, company, salary, location, experience, status)
VACANCIES = [
    (
        "Senior Python Developer",
        "Северная Звезда",
        "от 320 000 ₽ на руки",
        "Москва",
        "3–6 лет",
        ProcessingState.LETTER_READY,
    ),
    (
        "Бэкенд-разработчик (FastAPI)",
        "Контур Данных",
        "250 000 — 350 000 ₽",
        "Санкт-Петербург",
        "3–6 лет",
        ProcessingState.LETTER_READY,
    ),
    (
        "Team Lead Backend",
        "Ортус Технологии",
        "от 400 000 ₽",
        "Удалённо",
        "более 6 лет",
        ProcessingState.LETTER_READY,
    ),
    (
        "Python-разработчик в платформенную команду",
        "Ирида",
        "280 000 — 340 000 ₽",
        "Москва",
        "3–6 лет",
        ProcessingState.LETTER_PENDING,
    ),
    (
        "Разработчик высоконагруженных сервисов",
        "Гринвич Лаб",
        "от 300 000 ₽",
        "Удалённо",
        "3–6 лет",
        ProcessingState.LETTER_SENT,
    ),
    (
        "Backend Engineer (Python/Go)",
        "Аркадия Софт",
        "по итогам собеседования",
        "Новосибирск",
        "3–6 лет",
        ProcessingState.LETTER_SENT,
    ),
    (
        "Ведущий инженер, интеграции",
        "Меридиан Цифра",
        "270 000 — 330 000 ₽",
        "Казань",
        "более 6 лет",
        ProcessingState.ERROR,
    ),
]

DESCRIPTION = (
    "Мы развиваем платформу для управления цепочками поставок. Команда из "
    "восьми инженеров, вы будете отвечать за сервисы приёма и обработки "
    "заказов.\n\n"
    "Ожидаем: уверенный Python, опыт с асинхронными фреймворками, понимание "
    "реляционных БД и очередей. Плюсом будет опыт наставничества.\n\n"
    "Предлагаем: гибкий график, ДМС, оплату конференций, выбор техники."
)

LETTER = """Здравствуйте!

Откликаюсь на позицию «{title}» в компании «{company}».

Последние шесть лет пишу бэкенд на Python: FastAPI, SQLAlchemy, asyncio.
В прошлом проекте отвечал за биллинг и интеграции с платёжными провайдерами —
сервис держал около 3000 RPS, и мне пришлось вплотную заняться и профилем
нагрузки, и отказоустойчивостью очередей.

Из вашего описания зацепило, что команда небольшая и инженер отвечает за
сервис целиком, а не за отдельный слой. Последние два года я как раз работаю
техлидом четырёх человек: веду ревью, принимаю архитектурные решения и
участвую в найме, — и мне важно, чтобы за код можно было отвечать от идеи
до продакшена.

Готов обсудить детали и, если нужно, разобрать любой из своих проектов
подробнее.

С уважением,
Алексей"""

CHAT = [
    ("user", "Сделай короче и убери формальности в конце", None),
    (
        "assistant",
        "Сократил до трёх абзацев и убрал подпись-клише. Основной акцент "
        "оставил на нагрузке 3000 RPS и опыте техлида — это ближе всего к "
        "вашим требованиям.",
        2,
    ),
]


async def main() -> None:
    paths = AppPaths()
    db = paths.db_file

    if Path.home() == Path("/home/bimba"):
        sys.exit(
            "Refusing to seed inside the real home directory.\n"
            "Run with an isolated HOME, e.g.\n"
            "  HOME=/tmp/otklik-demo uv run python scripts/seed_demo_db.py"
        )

    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()

    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now()

    async with factory() as session:  # type: AsyncSession
        session.add(
            SettingsORM(
                id=1,
                letter_style=LETTER_STYLE,
                resume_text=RESUME,
                max_pages=3,
                max_vacancies=40,
                daily_limit=30,
                hourly_limit=8,
                min_delay_ms=45_000,
                delay_jitter_ms=15_000,
                auto_submit=False,
                llm_deployments=DEPLOYMENTS,
                llm_system_prompt=SYSTEM_PROMPT,
            )
        )
        session.add(
            SearchHistoryORM(
                id=SEARCH_ID,
                url="https://hh.ru/search/vacancy?text=python+backend&area=1",
                max_pages=3,
                max_vacancies=40,
                status=SearchStatusAPISchema.FINISHED,
                parsed_pages=3,
                parsed_vacancies=len(VACANCIES),
                started_at=now - timedelta(minutes=18),
                finished_at=now - timedelta(minutes=14),
            )
        )
        await session.commit()

        for index, (title, company, salary, location, experience, state) in enumerate(
            VACANCIES
        ):
            vacancy = VacancyORM(
                title=title,
                apply_link=f"https://hh.ru/vacancy/{90_000_000 + index}",
                description=DESCRIPTION,
                company_name=company,
                salary=salary,
                work_location=location,
                work_experience=experience,
                published_at="сегодня",
                updated_at="сегодня",
                work_formats=["Удалённо"] if "Удалённо" in location else ["Гибрид"],
                employment_types=["Полная занятость"],
            )
            session.add(vacancy)
            await session.flush()

            await session.execute(
                search_vacancies_table.insert().values(
                    search_id=SEARCH_ID, vacancy_id=vacancy.id
                )
            )

            application = ApplicationORM(
                vacancy_id=vacancy.id,
                status=state,
                error_message="hh.ru показал капчу — отклик не отправлен"
                if state is ProcessingState.ERROR
                else None,
                created_at=now - timedelta(minutes=16 - index),
                updated_at=now - timedelta(minutes=6 - index // 2),
            )
            session.add(application)
            await session.flush()

            # LETTER_PENDING = письмо ещё генерируется, текста быть не должно.
            if state is ProcessingState.LETTER_PENDING:
                continue

            text = LETTER.format(title=title, company=company)
            session.add(
                CoverLetterORM(
                    application_id=application.id,
                    version=1,
                    text=text,
                    source="generated",
                    created_at=now - timedelta(minutes=12 - index),
                )
            )

            # У первой вакансии — история версий и переписка с AI: кадр шага 4
            # должен показывать диалог, а не пустую панель.
            if index == 0:
                shorter = "\n\n".join(text.split("\n\n")[:3]) + "\n\nАлексей"
                session.add(
                    CoverLetterORM(
                        application_id=application.id,
                        version=2,
                        text=shorter,
                        source="chat",
                        created_at=now - timedelta(minutes=9),
                    )
                )
                for order, (role, content, produced) in enumerate(CHAT):
                    session.add(
                        ChatMessageORM(
                            application_id=application.id,
                            role=role,
                            content=content,
                            produced_version=produced,
                            created_at=now - timedelta(minutes=10 - order),
                        )
                    )

        await session.commit()

    await engine.dispose()

    print(f"Demo database seeded: {db}")
    print(f"  HOME             : {Path.home()}")
    print(f"  vacancies        : {len(VACANCIES)}")
    print(
        "  statuses         : 3 готовы к отклику, 1 генерируется, 2 отправлены, 1 ошибка"
    )
    print("  real data touched: none")


if __name__ == "__main__":
    if "HOME" not in os.environ:
        sys.exit("HOME must be set explicitly.")
    asyncio.run(main())
