from otklik_backend.sites.kwork.selectors import KWORK_RESPONSE
from otklik_backend.sites.kwork.writer import KworkWriter


class FakeHandle:
    def __init__(
        self,
        text: str = "",
        placeholder: str | None = None,
        visible: bool = True,
    ) -> None:
        self._text = text
        self._placeholder = placeholder
        self._visible = visible

    async def text_content(self) -> str:
        return self._text

    async def get_attribute(self, name: str) -> str | None:
        return self._placeholder

    async def is_visible(self) -> bool:
        return self._visible


class FakePage:
    def __init__(
        self,
        price_placeholder: str | None = None,
        budget: str = "",
        h1s: list[FakeHandle] | None = None,
        order_name_handle: FakeHandle | None = None,
    ) -> None:
        self._price_placeholder = price_placeholder
        self._budget = budget
        self._h1s = h1s or []
        self._order_name_handle = order_name_handle
        self.filled: list[tuple[str, str]] = []

    async def query_selector(self, selector: str) -> FakeHandle | None:
        if selector == KWORK_RESPONSE.price_input:
            return FakeHandle(placeholder=self._price_placeholder)
        if selector == KWORK_RESPONSE.order_name_editor:
            return self._order_name_handle
        return None

    async def query_selector_all(self, selector: str) -> list[FakeHandle]:
        return self._h1s if selector == "h1" else []

    async def text_content(self, selector: str) -> str | None:
        return self._budget if selector == KWORK_RESPONSE.buyer_budget else None

    async def fill(
        self, selector: str, text: str, timeout: float | None = None
    ) -> None:
        self.filled.append((selector, text))


def _writer() -> KworkWriter:
    return KworkWriter(core=None, min_delay_ms=0, jitter_delay_ms=0)  # type: ignore[arg-type]


async def test_price_uses_buyer_budget_clamped_to_the_form_range() -> None:
    page = FakePage(
        price_placeholder="800 - 12 000",
        budget="Желаемый бюджет: до 4000 ₽ Допустимый: до 12000 ₽",
    )
    assert await _writer()._pick_price(page) == 4000  # type: ignore[arg-type]


async def test_price_falls_back_to_the_low_bound_without_a_budget() -> None:
    page = FakePage(price_placeholder="800 - 12 000", budget="")
    assert await _writer()._pick_price(page) == 800  # type: ignore[arg-type]


async def test_price_is_capped_at_the_form_maximum() -> None:
    page = FakePage(price_placeholder="800 - 12 000", budget="до 50000 ₽")
    assert await _writer()._pick_price(page) == 12000  # type: ignore[arg-type]


async def test_price_at_100_percent_reaches_the_acceptable_budget() -> None:
    page = FakePage(
        price_placeholder="800 - 12 000",
        budget="Желаемый бюджет: до 4000 ₽ Допустимый: до 12000 ₽",
    )
    assert await _writer()._pick_price(page, 100) == 12000  # type: ignore[arg-type]


async def test_price_at_50_percent_lands_between_desired_and_acceptable() -> None:
    page = FakePage(
        price_placeholder="800 - 12 000",
        budget="Желаемый бюджет: до 4000 ₽ Допустимый: до 12000 ₽",
    )
    assert await _writer()._pick_price(page, 50) == 8000  # type: ignore[arg-type]


async def test_price_percent_is_clamped_to_the_form_maximum() -> None:
    page = FakePage(
        price_placeholder="800 - 12 000",
        budget="Желаемый бюджет: до 4000 ₽ Допустимый: до 20000 ₽",
    )
    assert await _writer()._pick_price(page, 100) == 12000  # type: ignore[arg-type]


async def test_project_title_skips_the_offer_button_heading() -> None:
    page = FakePage(
        h1s=[FakeHandle("Предложить услугу"), FakeHandle("Снять разметку ВК")]
    )
    assert await _writer()._project_title(page) == "Снять разметку ВК"  # type: ignore[arg-type]


async def test_order_name_is_skipped_when_its_field_is_hidden() -> None:
    page = FakePage(
        h1s=[FakeHandle("Снять разметку ВК")],
        order_name_handle=FakeHandle(visible=False),
    )
    await _writer()._fill_order_name(page)  # type: ignore[arg-type]
    assert page.filled == []


async def test_order_name_is_filled_with_the_title_when_visible() -> None:
    page = FakePage(
        h1s=[FakeHandle("Снять разметку ВК")],
        order_name_handle=FakeHandle(visible=True),
    )
    await _writer()._fill_order_name(page)  # type: ignore[arg-type]
    assert page.filled == [(KWORK_RESPONSE.order_name_editor, "Снять разметку ВК")]


class _FakeVacancy:
    title = "Телеграм-бот"
    description = "aiogram, вебхуки"


class _FakeAI:
    def __init__(self, days: int | None) -> None:
        self._days = days

    async def estimate_delivery_days(self, title: str, description: str) -> int | None:
        return self._days


class _FakeSession:
    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


def _fake_session_maker() -> _FakeSession:
    return _FakeSession()


def _writer_with_ai(days: int | None) -> KworkWriter:
    return KworkWriter(
        core=None,  # type: ignore[arg-type]
        min_delay_ms=0,
        jitter_delay_ms=0,
        session_maker=_fake_session_maker,  # type: ignore[arg-type]
        ai_layer=_FakeAI(days),  # type: ignore[arg-type]
    )


async def test_delivery_days_default_without_ai_layer() -> None:
    assert await _writer()._estimate_delivery_days("https://kwork.ru/projects/1") == 3


async def test_delivery_days_uses_the_estimate(monkeypatch) -> None:
    from otklik_backend.db.repositories.vacancies import VacancyRepository

    async def fake_get(cls, session, apply_link):  # type: ignore[no-untyped-def]
        return _FakeVacancy()

    monkeypatch.setattr(VacancyRepository, "get_by_apply_link", classmethod(fake_get))
    assert await _writer_with_ai(7)._estimate_delivery_days("url") == 7


async def test_delivery_days_are_clamped_to_the_maximum(monkeypatch) -> None:
    from otklik_backend.db.repositories.vacancies import VacancyRepository

    async def fake_get(cls, session, apply_link):  # type: ignore[no-untyped-def]
        return _FakeVacancy()

    monkeypatch.setattr(VacancyRepository, "get_by_apply_link", classmethod(fake_get))
    assert await _writer_with_ai(999)._estimate_delivery_days("url") == 30


async def test_delivery_days_fall_back_when_estimate_is_none(monkeypatch) -> None:
    from otklik_backend.db.repositories.vacancies import VacancyRepository

    async def fake_get(cls, session, apply_link):  # type: ignore[no-untyped-def]
        return _FakeVacancy()

    monkeypatch.setattr(VacancyRepository, "get_by_apply_link", classmethod(fake_get))
    assert await _writer_with_ai(None)._estimate_delivery_days("url") == 3
