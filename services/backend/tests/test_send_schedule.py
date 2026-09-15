from datetime import datetime, timedelta

from otklik_backend.orchestrator.send_schedule import project_schedule


NOW = datetime(2026, 9, 15, 12, 0, 0)


def test_under_limits_first_goes_now_and_rest_are_paced() -> None:
    schedule = project_schedule(
        now=NOW,
        past_events=[],
        queued_vacancy_ids=[10, 11, 12],
        hourly_limit=100,
        daily_limit=1000,
        pacing_seconds=60,
    )

    assert schedule[10] == NOW
    assert schedule[11] == NOW + timedelta(seconds=60)
    assert schedule[12] == NOW + timedelta(seconds=120)


def test_hourly_limit_reached_waits_for_the_oldest_in_window_to_age_out() -> None:
    past = [NOW - timedelta(minutes=m) for m in (50, 40, 30, 20, 10)]

    schedule = project_schedule(
        now=NOW,
        past_events=past,
        queued_vacancy_ids=[7],
        hourly_limit=5,
        daily_limit=1000,
        pacing_seconds=60,
    )

    assert schedule[7] == NOW - timedelta(minutes=50) + timedelta(hours=1)


def test_daily_limit_reached_waits_for_the_day_window() -> None:
    past = [NOW - timedelta(hours=h) for h in (23, 20, 10, 5, 2)]

    schedule = project_schedule(
        now=NOW,
        past_events=past,
        queued_vacancy_ids=[9],
        hourly_limit=100,
        daily_limit=5,
        pacing_seconds=60,
    )

    assert schedule[9] == NOW - timedelta(hours=23) + timedelta(days=1)


def test_stale_events_outside_the_day_window_do_not_constrain() -> None:
    past = [NOW - timedelta(hours=30), NOW - timedelta(hours=48)]

    schedule = project_schedule(
        now=NOW,
        past_events=past,
        queued_vacancy_ids=[1],
        hourly_limit=1,
        daily_limit=1,
        pacing_seconds=0,
    )

    assert schedule[1] == NOW
