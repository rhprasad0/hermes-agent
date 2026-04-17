from datetime import datetime
from zoneinfo import ZoneInfo

from va_toll_ingest.time_windows import parse_window, should_poll


def test_parse_window_returns_start_and_end_times():
    window = parse_window("06:00-10:00")

    assert window.start.hour == 6
    assert window.start.minute == 0
    assert window.end.hour == 10
    assert window.end.minute == 0


def test_should_poll_returns_true_inside_any_window():
    eastern = ZoneInfo("America/New_York")
    now = datetime(2026, 4, 17, 8, 15, tzinfo=eastern)
    windows = [parse_window("06:00-10:00"), parse_window("15:00-19:00")]

    assert should_poll(now, windows) is True


def test_should_poll_returns_false_outside_all_windows():
    eastern = ZoneInfo("America/New_York")
    now = datetime(2026, 4, 17, 13, 30, tzinfo=eastern)
    windows = [parse_window("06:00-10:00"), parse_window("15:00-19:00")]

    assert should_poll(now, windows) is False


def test_should_poll_returns_false_on_weekends_even_inside_window():
    eastern = ZoneInfo("America/New_York")
    now = datetime(2026, 4, 19, 8, 15, tzinfo=eastern)
    windows = [parse_window("06:00-10:00"), parse_window("15:00-19:00")]

    assert should_poll(now, windows) is False
