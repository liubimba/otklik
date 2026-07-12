import pytest
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from otklik_backend.api.schemas import VacancyAPISchema, VacancyListPageAPISchema
from otklik_backend.core.state import ProcessingState
from otklik_backend.db.models import ApplicationORM, VacancyORM


def test_vacancies_get(client):
    response: Response = client.get("/api/v1/vacancies")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)

    for item in payload:
        VacancyAPISchema.model_validate(item)


def test_vacancies_get_by_id(client):
    response: Response = client.get("/api/v1/vacancies/1")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    VacancyAPISchema.model_validate(payload)


def test_vacancies_get_by_id_not_found(client):
    response: Response = client.get("/api/v1/vacancies/999")
    assert response.status_code == 404


# ─ GET /vacancies/all ────────────────────────────────────────────────
#
# The `client` fixture already seeds vacancy id=1 with no application row.
# `seeded_applications` adds three more, each in a distinct state.


@pytest.fixture
async def seeded_applications(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    states = [
        ProcessingState.PARSED,
        ProcessingState.LETTER_READY,
        ProcessingState.ERROR,
    ]
    async with session_factory() as session:
        for i, _ in enumerate(states, start=2):
            session.add(
                VacancyORM(
                    id=i,
                    title=f"Vacancy {i}",
                    apply_link=f"https://hh.ru/vacancy/{i}",
                    description="desc",
                    work_formats=[],
                    employment_types=[],
                )
            )
        # VacancyORM and ApplicationORM have no relationship() between them —
        # only a bare ForeignKey — so a single flush gives no ordering guarantee
        # and the FK would fail. Land the parents first.
        await session.flush()

        for i, state in enumerate(states, start=2):
            session.add(ApplicationORM(vacancy_id=i, status=state))
        await session.commit()


def test_list_all_returns_envelope_and_null_status(client) -> None:
    """Also guards the route-ordering trap: "/all" must not be captured by the
    int-typed GET /{vacancy_id}, which would 422."""
    response: Response = client.get("/api/v1/vacancies/all")
    assert response.status_code == 200

    page = VacancyListPageAPISchema.model_validate(response.json())
    assert page.total == 1
    assert len(page.items) == 1
    assert page.items[0].id == 1
    assert page.items[0].status is None


def test_list_all_carries_status_inline(client, seeded_applications: None) -> None:
    response: Response = client.get("/api/v1/vacancies/all")
    assert response.status_code == 200

    page = VacancyListPageAPISchema.model_validate(response.json())
    assert page.total == 4
    by_id = {item.id: item.status for item in page.items}
    assert by_id == {
        1: None,
        2: ProcessingState.PARSED,
        3: ProcessingState.LETTER_READY,
        4: ProcessingState.ERROR,
    }


def test_list_all_orders_newest_first(client, seeded_applications: None) -> None:
    response: Response = client.get("/api/v1/vacancies/all")
    page = VacancyListPageAPISchema.model_validate(response.json())
    assert [item.id for item in page.items] == [4, 3, 2, 1]


def test_list_all_filters_by_single_status(client, seeded_applications: None) -> None:
    response: Response = client.get("/api/v1/vacancies/all?status=letter_ready")
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 1
    assert [item.id for item in page.items] == [3]


def test_list_all_filters_by_multiple_statuses(
    client, seeded_applications: None
) -> None:
    response: Response = client.get(
        "/api/v1/vacancies/all?status=letter_ready&status=error"
    )
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 2
    assert [item.id for item in page.items] == [4, 3]


def test_list_all_none_filter_matches_missing_and_parsed(
    client, seeded_applications: None
) -> None:
    """«Без отклика» — the two shapes that draw no badge: no application row at
    all (id=1) and one still sitting in `parsed` (id=2)."""
    response: Response = client.get("/api/v1/vacancies/all?status=none")
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 2
    assert [item.id for item in page.items] == [2, 1]


def test_list_all_none_filter_combines_with_a_real_status(
    client, seeded_applications: None
) -> None:
    response: Response = client.get("/api/v1/vacancies/all?status=none&status=error")
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 3
    assert [item.id for item in page.items] == [4, 2, 1]


def test_list_all_paginates_while_total_stays_full(
    client, seeded_applications: None
) -> None:
    first: Response = client.get("/api/v1/vacancies/all?limit=2&offset=0")
    second: Response = client.get("/api/v1/vacancies/all?limit=2&offset=2")

    first_page = VacancyListPageAPISchema.model_validate(first.json())
    second_page = VacancyListPageAPISchema.model_validate(second.json())

    assert first_page.total == second_page.total == 4
    assert [item.id for item in first_page.items] == [4, 3]
    assert [item.id for item in second_page.items] == [2, 1]


# ─ free-text search ──────────────────────────────────────────────────


@pytest.fixture
async def seeded_searchable(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rows = [
        (10, "Python-разработчик", "Ozon", "Django и FastAPI"),
        (11, "Go разработчик", "Ozon", "Микросервисы на Go"),
        (12, "Frontend Developer", "Yandex", "React, 100% удалёнка"),
    ]
    async with session_factory() as session:
        for vacancy_id, title, company, description in rows:
            session.add(
                VacancyORM(
                    id=vacancy_id,
                    title=title,
                    apply_link=f"https://hh.ru/vacancy/{vacancy_id}",
                    description=description,
                    company_name=company,
                    work_formats=[],
                    employment_types=[],
                )
            )
        await session.commit()


def test_search_matches_title_case_insensitively(
    client, seeded_searchable: None
) -> None:
    """SQLite's own lower()/LIKE only fold ASCII, so a Cyrillic query is the
    real test of the py_lower UDF."""
    response: Response = client.get("/api/v1/vacancies/all?q=РАЗРАБОТЧИК")
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 2
    assert [item.id for item in page.items] == [11, 10]


def test_search_matches_company_and_description(
    client, seeded_searchable: None
) -> None:
    by_company = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?q=ozon").json()
    )
    assert [item.id for item in by_company.items] == [11, 10]

    by_description = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?q=fastapi").json()
    )
    assert [item.id for item in by_description.items] == [10]


def test_search_ands_words_together(client, seeded_searchable: None) -> None:
    """«python ozon» narrows; it does not union the two words' matches."""
    response: Response = client.get("/api/v1/vacancies/all?q=python+ozon")
    page = VacancyListPageAPISchema.model_validate(response.json())

    assert page.total == 1
    assert [item.id for item in page.items] == [10]


def test_search_words_may_match_different_columns(
    client, seeded_searchable: None
) -> None:
    response: Response = client.get("/api/v1/vacancies/all?q=go+микросервисы")
    page = VacancyListPageAPISchema.model_validate(response.json())
    assert [item.id for item in page.items] == [11]


def test_search_treats_like_metacharacters_literally(
    client, seeded_searchable: None
) -> None:
    """A bare `%` must not match everything."""
    matched = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?q=100%25").json()
    )
    assert [item.id for item in matched.items] == [12]

    underscore = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?q=_").json()
    )
    assert underscore.total == 0


def test_blank_search_is_ignored(client, seeded_searchable: None) -> None:
    page = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?q=%20%20").json()
    )
    assert page.total == 4  # 3 seeded + the fixture's vacancy id=1


def test_search_and_status_filter_narrow_together(
    client, seeded_applications: None, seeded_searchable: None
) -> None:
    """Ticked chips OR among themselves, but AND with the text query."""
    page = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?status=none&q=разработчик").json()
    )
    # Both searchable vacancies are unapplied, so the chip keeps them...
    assert [item.id for item in page.items] == [11, 10]

    # ...while a chip they cannot satisfy empties the result.
    narrowed = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?status=error&q=разработчик").json()
    )
    assert narrowed.total == 0


def test_multiple_status_chips_union(client, seeded_applications: None) -> None:
    """Checkbox semantics: «Готово» + «Пропущено» shows both, not neither."""
    page = VacancyListPageAPISchema.model_validate(
        client.get("/api/v1/vacancies/all?status=letter_ready&status=none").json()
    )
    assert [item.id for item in page.items] == [3, 2, 1]


def test_list_all_rejects_unknown_status(client) -> None:
    assert client.get("/api/v1/vacancies/all?status=bogus").status_code == 422


def test_list_all_rejects_zero_limit(client) -> None:
    assert client.get("/api/v1/vacancies/all?limit=0").status_code == 422
