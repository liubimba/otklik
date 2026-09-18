from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import SearchStatusAPISchema, VacancyAPISchema
from otklik_backend.core.board import Board
from otklik_backend.db.models import SearchHistoryORM
from otklik_backend.db.repositories.search_history import SearchHistoryRepository
from otklik_backend.db.repositories.vacancies import VacancyRepository


def _vacancy(i: int) -> VacancyAPISchema:
    return VacancyAPISchema(
        title=f"v{i}",
        apply_link=f"https://example.test/vacancy/{i}",
        description=f"desc {i}",
    )


async def _seed_search(
    session: AsyncSession, search_id: str, board: Board, vacancy_ids: list[int]
) -> None:
    await SearchHistoryRepository.create(
        session=session,
        search_id=search_id,
        board=board,
        url="https://example.test/search",
        max_vacancies=50,
        max_pages=1,
        search_status=SearchStatusAPISchema.FINISHED,
    )
    for i in vacancy_ids:
        vacancy = await VacancyRepository.upsert(session=session, vacancy=_vacancy(i))
        await VacancyRepository.link_to_search(
            session=session, search_id=search_id, vacancy_id=vacancy.id
        )
    await session.commit()


async def test_board_column_stores_and_reads_the_lowercase_value(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _seed_search(session, "s1", Board.HH_RU, [])

        raw = (
            await session.execute(text("SELECT board FROM searches WHERE id = 's1'"))
        ).scalar_one()
        assert raw == "hh_ru"

        row = await session.get(SearchHistoryORM, "s1")
        assert row is not None
        assert row.board is Board.HH_RU


async def test_get_latest_id_is_scoped_per_board(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _seed_search(session, "hh-old", Board.HH_RU, [1])
        await _seed_search(session, "habr-1", Board.HABR, [2])
        await _seed_search(session, "hh-new", Board.HH_RU, [3])

        assert (
            await SearchHistoryRepository.get_latest_id(session, board=Board.HH_RU)
            == "hh-new"
        )
        assert (
            await SearchHistoryRepository.get_latest_id(session, board=Board.HABR)
            == "habr-1"
        )
        assert await SearchHistoryRepository.get_latest_id(session) == "hh-new"


async def test_history_list_is_scoped_per_board(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _seed_search(session, "hh-1", Board.HH_RU, [1])
        await _seed_search(session, "habr-1", Board.HABR, [2])

        hh_rows = await SearchHistoryRepository.list_all(session, board=Board.HH_RU)
        habr_rows = await SearchHistoryRepository.list_all(session, board=Board.HABR)
        all_rows = await SearchHistoryRepository.list_all(session)

        assert {r.id for r in hh_rows} == {"hh-1"}
        assert {r.id for r in habr_rows} == {"habr-1"}
        assert {r.id for r in all_rows} == {"hh-1", "habr-1"}


async def test_vacancy_listing_is_scoped_per_board(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _seed_search(session, "hh-1", Board.HH_RU, [1, 2])
        await _seed_search(session, "habr-1", Board.HABR, [3])

        hh_all = await VacancyRepository.list_all(session, board=Board.HH_RU)
        habr_all = await VacancyRepository.list_all(session, board=Board.HABR)
        assert {v.title for v in hh_all} == {"v1", "v2"}
        assert {v.title for v in habr_all} == {"v3"}

        hh_rows, hh_total = await VacancyRepository.list_with_status(
            session=session, board=Board.HH_RU
        )
        habr_rows, habr_total = await VacancyRepository.list_with_status(
            session=session, board=Board.HABR
        )
        assert hh_total == 2
        assert habr_total == 1
        assert {row[0].title for row in habr_rows} == {"v3"}
