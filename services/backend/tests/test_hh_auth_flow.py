from otklik_backend.sites.hh_ru.auth_flow import HHRUAuthFlow


class _FakePage:
    def __init__(self, closed: bool = False) -> None:
        self._closed = closed

    def is_closed(self) -> bool:
        return self._closed

    async def bring_to_front(self) -> None:
        pass

    async def close(self) -> None:
        self._closed = True


class _FakeBrowser:
    def __init__(
        self,
        *,
        cookies: list[dict[str, str]] | None = None,
        raise_on_cookies: bool = False,
        page_closed: bool = False,
        authorize_on_call: int | None = None,
    ) -> None:
        self._cookies = cookies or []
        self.raise_on_cookies = raise_on_cookies
        self.authorize_on_call = authorize_on_call
        self.page = _FakePage(closed=page_closed)
        self.new_page_calls = 0
        self.hidden = False
        self.cleared = False
        self._cookie_calls = 0

    async def cookies(self, base_url: str) -> list[dict[str, str]]:
        self._cookie_calls += 1
        if self.raise_on_cookies:
            raise RuntimeError("Target page, context or browser has been closed")
        if (
            self.authorize_on_call is not None
            and self._cookie_calls >= self.authorize_on_call
        ):
            return [{"name": "hhrole", "value": "applicant"}]
        return self._cookies

    async def new_page(self, url: str) -> _FakePage:
        self.new_page_calls += 1
        return self.page

    async def show_window(self) -> None:
        pass

    async def hide_window(self) -> None:
        self.hidden = True

    async def clear_cookies(self) -> None:
        self.cleared = True


def _flow(browser: _FakeBrowser) -> HHRUAuthFlow:
    return HHRUAuthFlow(browser)  # type: ignore[arg-type]


class _ColdProfileBrowser(_FakeBrowser):
    async def cookies(self, base_url: str) -> list[dict[str, str]]:
        self._cookie_calls += 1
        if self.new_page_calls > 0:
            return [{"name": "hhrole", "value": "applicant"}]
        return []


async def test_get_auth_status_primes_hh_navigation_for_a_logged_in_cold_profile() -> (
    None
):
    browser = _ColdProfileBrowser()
    flow = _flow(browser)

    status = await flow.get_auth_status()

    assert status.status == "authorized"
    assert browser.new_page_calls == 1
    assert browser.hidden is True


async def test_get_auth_status_primes_only_once_when_really_logged_out() -> None:
    browser = _FakeBrowser(cookies=[])
    flow = _flow(browser)

    first = await flow.get_auth_status()
    second = await flow.get_auth_status()

    assert first.status == "unauthorized"
    assert second.status == "unauthorized"
    assert browser.new_page_calls == 1


async def test_get_auth_status_skips_priming_when_cookie_already_shows_auth() -> None:
    browser = _FakeBrowser(cookies=[{"name": "hhrole", "value": "applicant"}])
    flow = _flow(browser)

    status = await flow.get_auth_status()

    assert status.status == "authorized"
    assert browser.new_page_calls == 0


async def test_get_auth_status_is_unauthorized_when_browser_is_dead() -> None:
    status = await _flow(_FakeBrowser(raise_on_cookies=True)).get_auth_status()
    assert status.status == "unauthorized"


async def test_get_auth_status_authorized_from_role_cookie() -> None:
    browser = _FakeBrowser(cookies=[{"name": "hhrole", "value": "applicant"}])
    status = await _flow(browser).get_auth_status()
    assert status.status == "authorized"


async def test_wait_for_login_treats_closed_window_as_cancel() -> None:
    browser = _FakeBrowser(page_closed=True)
    flow = _flow(browser)

    await flow.wait_for_login(poll_interval=0)

    assert flow._auth_status.status == "unauthorized"
    assert browser.new_page_calls == 1
    assert browser.hidden is True


async def test_wait_for_login_survives_browser_dying_mid_wait() -> None:
    browser = _FakeBrowser(page_closed=True, raise_on_cookies=True)
    flow = _flow(browser)

    await flow.wait_for_login(poll_interval=0)

    assert flow._auth_status.status == "unauthorized"


async def test_wait_for_login_authorizes_when_cookie_appears() -> None:
    browser = _FakeBrowser(authorize_on_call=2)
    flow = _flow(browser)

    await flow.wait_for_login(poll_interval=0)

    assert flow._auth_status.status == "authorized"
