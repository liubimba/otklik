from otklik_backend.browser.chromium_gate import ChromiumGate

BASIC_PROGRESS_LINE = "|■■■■■■■■                | 40% of 164.9 MiB"


def test_parses_percent_and_total_from_the_patchright_progress_line() -> None:
    progress = ChromiumGate.parse_progress(BASIC_PROGRESS_LINE)
    assert progress is not None
    assert progress.percent == 40.0
    assert progress.total_bytes == int(164.9 * 1024 * 1024)
    assert progress.done is False


def test_parses_a_zero_percent_line() -> None:
    progress = ChromiumGate.parse_progress(
        "|                        |  0% of 164.9 MiB"
    )
    assert progress is not None
    assert progress.percent == 0.0


def test_hundred_percent_is_not_done_until_the_process_exits() -> None:
    progress = ChromiumGate.parse_progress(
        "|■■■■■■■■■■■■■■■■■■■■■■■■| 100% of 164.9 MiB"
    )
    assert progress is not None
    assert progress.percent == 100.0
    assert progress.done is False


def test_ignores_lines_that_carry_no_progress() -> None:
    assert (
        ChromiumGate.parse_progress("Downloading Chromium 133.0 from https://x") is None
    )
    assert ChromiumGate.parse_progress("") is None
