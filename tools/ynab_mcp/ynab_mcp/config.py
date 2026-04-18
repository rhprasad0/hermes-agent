from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from os import environ
from pathlib import Path
from re import fullmatch
from typing import Mapping

from .errors import YnabConfigError


@dataclass(frozen=True)
class Settings:
    access_token: str
    plan_id: str = "default"
    base_url: str = "https://api.ynab.com/v1"
    timeout: int = 30

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None, *, env_file: str | None = None) -> "Settings":
        env = dict(environ)
        explicit = dict(values or {})
        env_path = explicit.get("YNAB_ENV_FILE") or env_file or env.get("YNAB_ENV_FILE") or env.get("YNAB_TOKEN_FILE")
        if env_path:
            env.update(load_env_file(Path(env_path).expanduser()))
        env.update(explicit)

        access_token = env.get("YNAB_ACCESS_TOKEN", "").strip()
        if not access_token:
            raise YnabConfigError("missing required environment variable: YNAB_ACCESS_TOKEN")

        plan_id = env.get("YNAB_PLAN_ID", "default").strip() or "default"
        base_url = env.get("YNAB_BASE_URL", "https://api.ynab.com/v1").strip() or "https://api.ynab.com/v1"
        timeout_raw = env.get("YNAB_TIMEOUT", "30").strip() or "30"

        try:
            timeout = int(timeout_raw)
        except ValueError as exc:
            raise YnabConfigError("YNAB_TIMEOUT must be an integer") from exc

        return cls(
            access_token=access_token,
            plan_id=plan_id,
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise YnabConfigError(f"YNAB env file not found: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def normalize_month(value: str, *, today: date | None = None) -> str:
    raw = (value or "current").strip()
    if raw == "":
        raw = "current"

    if raw.casefold() == "current":
        current = today or date.today()
        return current.replace(day=1).isoformat()

    if fullmatch(r"\d{4}-\d{2}", raw):
        return f"{raw}-01"

    if fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw

    raise YnabConfigError("month must be 'current', YYYY-MM, or YYYY-MM-DD")
