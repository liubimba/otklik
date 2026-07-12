from otklik_backend.browser.window import BesidePlacement, Rect


def test_places_browser_to_the_right_when_there_is_room() -> None:
    app = Rect(x=100, y=100, width=800, height=600)
    placement = BesidePlacement(
        screen_width=2560, screen_height=1440, browser_width=1024
    )

    result = placement.beside(app)

    # Right of the app (app.x + app.width + gap), same top, app height.
    assert result == Rect(x=912, y=100, width=1024, height=600)


def test_overlays_centred_on_app_when_no_room_on_the_right() -> None:
    app = Rect(x=1600, y=100, width=800, height=600)
    placement = BesidePlacement(
        screen_width=2560, screen_height=1440, browser_width=1024
    )

    result = placement.beside(app)

    # 1600 + 800 + 12 + 1024 overflows 2560, so it centres on the app instead.
    assert result.width == 1024
    assert result.x == 1600 + (800 - 1024) // 2
    assert result.x + result.width <= 2560


def test_clamps_vertically_so_the_window_stays_on_screen() -> None:
    app = Rect(x=100, y=1300, width=800, height=600)
    placement = BesidePlacement(
        screen_width=2560, screen_height=1440, browser_width=1024
    )

    result = placement.beside(app)

    assert result.y == 1440 - 600  # pushed up so y + height fits the screen


def test_never_wider_than_the_screen() -> None:
    app = Rect(x=0, y=0, width=400, height=600)
    placement = BesidePlacement(screen_width=800, screen_height=600, browser_width=1024)

    result = placement.beside(app)

    assert result.width == 800
    assert result.x == 0
    assert result.x + result.width <= 800
