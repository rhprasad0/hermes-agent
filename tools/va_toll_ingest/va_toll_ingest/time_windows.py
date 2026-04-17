from dataclasses import dataclass
from datetime import time, datetime


@dataclass(frozen=True)
class RushHourWindow:
    start: time
    end: time

    def contains(self, current: time) -> bool:
        return self.start <= current <= self.end


def parse_window(value: str) -> RushHourWindow:
    start_raw, end_raw = value.split("-", maxsplit=1)
    start_hour, start_minute = [int(part) for part in start_raw.split(":", maxsplit=1)]
    end_hour, end_minute = [int(part) for part in end_raw.split(":", maxsplit=1)]
    return RushHourWindow(
        start=time(hour=start_hour, minute=start_minute),
        end=time(hour=end_hour, minute=end_minute),
    )


def should_poll(now: datetime, windows: list[RushHourWindow]) -> bool:
    if now.weekday() >= 5:
        return False

    current = now.timetz().replace(tzinfo=None)
    return any(window.contains(current) for window in windows)
