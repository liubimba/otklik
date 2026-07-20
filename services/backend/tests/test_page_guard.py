from typing import Any

from otklik_backend.browser.guard import SinglePageGuard


class FakeFrame: ...


class FakePage:
    def __init__(self) -> None:
        self.main_frame = FakeFrame()


class FakeRequest:
    def __init__(self, url: str, frame: Any, is_navigation: bool = True) -> None:
        self.url = url
        self.frame = frame
        self._is_navigation = is_navigation

    def is_navigation_request(self) -> bool:
        return self._is_navigation


class FakeRoute:
    def __init__(self, request: FakeRequest) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    async def abort(self) -> None:
        self.aborted = True

    async def continue_(self) -> None:
        self.continued = True


def _guard_locked_to(page: FakePage) -> SinglePageGuard:
    guard = SinglePageGuard("hh.ru")
    guard.lock(page)  # type: ignore[arg-type]
    return guard


def test_a_page_other_than_the_locked_one_is_foreign() -> None:
    locked = FakePage()
    guard = _guard_locked_to(locked)

    assert guard.is_foreign(FakePage()) is True  # type: ignore[arg-type]
    assert guard.is_foreign(locked) is False  # type: ignore[arg-type]


def test_nothing_is_foreign_when_the_guard_is_not_locked() -> None:
    guard = SinglePageGuard("hh.ru")

    assert guard.active is False
    assert guard.is_foreign(FakePage()) is False  # type: ignore[arg-type]


def test_unlock_releases_the_lock() -> None:
    guard = _guard_locked_to(FakePage())
    guard.unlock()

    assert guard.active is False
    assert guard.is_foreign(FakePage()) is False  # type: ignore[arg-type]


def test_host_allows_the_site_and_its_subdomains() -> None:
    guard = SinglePageGuard("hh.ru")

    assert guard.host_allowed("https://hh.ru/search/vacancy") is True
    assert guard.host_allowed("https://novosibirsk.hh.ru/search/vacancy") is True
    assert guard.host_allowed("about:blank") is True


def test_host_rejects_other_sites_including_look_alikes() -> None:
    guard = SinglePageGuard("hh.ru")

    assert guard.host_allowed("https://google.com") is False
    assert guard.host_allowed("https://evilhh.ru/phish") is False


async def test_route_guard_aborts_top_level_navigation_off_the_host() -> None:
    page = FakePage()
    guard = _guard_locked_to(page)
    route = FakeRoute(FakeRequest("https://google.com", page.main_frame))

    await guard.guard_route(route)  # type: ignore[arg-type]

    assert route.aborted is True
    assert route.continued is False


async def test_route_guard_allows_navigation_within_the_host() -> None:
    page = FakePage()
    guard = _guard_locked_to(page)
    route = FakeRoute(FakeRequest("https://spb.hh.ru/search/vacancy", page.main_frame))

    await guard.guard_route(route)  # type: ignore[arg-type]

    assert route.continued is True
    assert route.aborted is False


async def test_route_guard_lets_subresource_requests_through() -> None:
    page = FakePage()
    guard = _guard_locked_to(page)
    route = FakeRoute(
        FakeRequest(
            "https://cdn.example.com/a.js", page.main_frame, is_navigation=False
        )
    )

    await guard.guard_route(route)  # type: ignore[arg-type]

    assert route.continued is True
    assert route.aborted is False


async def test_route_guard_ignores_navigation_in_other_frames() -> None:
    page = FakePage()
    guard = _guard_locked_to(page)
    route = FakeRoute(FakeRequest("https://google.com", FakeFrame()))

    await guard.guard_route(route)  # type: ignore[arg-type]

    assert route.continued is True
    assert route.aborted is False


async def test_route_guard_is_a_pass_through_when_unlocked() -> None:
    guard = SinglePageGuard("hh.ru")
    route = FakeRoute(FakeRequest("https://google.com", FakeFrame()))

    await guard.guard_route(route)  # type: ignore[arg-type]

    assert route.continued is True
    assert route.aborted is False
