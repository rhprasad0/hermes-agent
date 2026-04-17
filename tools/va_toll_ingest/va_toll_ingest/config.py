from dataclasses import dataclass
from os import environ
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from .time_windows import RushHourWindow, parse_window


@dataclass(frozen=True)
class Settings:
    vdot_toll_url: str
    vdot_toll_token: str
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str
    poll_tz: str
    am_window: RushHourWindow
    pm_window: RushHourWindow

    @property
    def windows(self) -> list[RushHourWindow]:
        return [self.am_window, self.pm_window]

    @property
    def connection_kwargs(self) -> dict[str, str | int]:
        return {
            "host": self.pg_host,
            "port": self.pg_port,
            "dbname": self.pg_database,
            "user": self.pg_user,
            "password": self.pg_password,
        }

    @classmethod
    def from_env(
        cls,
        values: Mapping[str, str] | None = None,
        *,
        require_token: bool = True,
        require_database: bool = True,
    ) -> "Settings":
        env = dict(environ if values is None else values)

        def get_required(name: str, default: str | None = None) -> str:
            value = env.get(name, default)
            if value is None or value == "":
                raise ValueError(f"missing required environment variable: {name}")
            return value

        vdot_toll_token = get_required("VDOT_TOLL_TOKEN") if require_token else env.get("VDOT_TOLL_TOKEN", "")
        pg_password = get_required("PGPASSWORD") if require_database else env.get("PGPASSWORD", "")

        return cls(
            vdot_toll_url=get_required(
                "VDOT_TOLL_URL",
                "https://data.511-atis-ttrip-prod.iteriscloud.com/smarterRoads/tollRoad/I95/current/tollingTripPricing_I95.csv",
            ),
            vdot_toll_token=vdot_toll_token,
            pg_host=get_required("PGHOST", "127.0.0.1"),
            pg_port=int(get_required("PGPORT", "5434")),
            pg_database=get_required("PGDATABASE", "va_tolling"),
            pg_user=get_required("PGUSER", "va_tolling_app"),
            pg_password=pg_password,
            poll_tz=get_required("POLL_TZ", "America/New_York"),
            am_window=parse_window(get_required("AM_WINDOW", "06:00-10:00")),
            pm_window=parse_window(get_required("PM_WINDOW", "15:00-19:00")),
        )


def sanitize_source_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
