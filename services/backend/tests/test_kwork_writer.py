from otklik_backend.sites.kwork.selectors import KWORK_RESPONSE
from otklik_backend.sites.kwork.writer import KworkWriter


class FakeHandle:
    def __init__(self, text: str = "", placeholder: str | None = None) -> None:
        self._text = text
        self._placeholder = placeholder

    async def text_content(self) -> str:
        return self._text

    async def get_attribute(self, name: str) -> str | None:
        return self._placeholder


class FakePage:
    def __init__(
        self,
        price_placeholder: str | None = None,
        budget: str = "",
        h1s: list[FakeHandle] | None = None,
    ) -> None:
        self._price_placeholder = price_placeholder
        self._budget = budget
        self._h1s = h1s or []

    async def query_selector(self, selector: str) -> FakeHandle | None:
        if selector == KWORK_RESPONSE.price_input:
            return FakeHandle(placeholder=self._price_placeholder)
        return None

    async def query_selector_all(self, selector: str) -> list[FakeHandle]:
        return self._h1s if selector == "h1" else []

    async def text_content(self, selector: str) -> str | None:
        return self._budget if selector == KWORK_RESPONSE.buyer_budget else None


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


async def test_project_title_skips_the_offer_button_heading() -> None:
    page = FakePage(
        h1s=[FakeHandle("Предложить услугу"), FakeHandle("Снять разметку ВК")]
    )
    assert await _writer()._project_title(page) == "Снять разметку ВК"  # type: ignore[arg-type]
