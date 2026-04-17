from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg

from .client import fetch_csv
from .config import Settings, sanitize_source_url
from .db import ensure_schema, upsert_trip_pricing_rows
from .normalize import parse_trip_pricing_csv
from .time_windows import should_poll


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Poll and store VDOT I-95/I-495 toll pricing data")
    parser.add_argument("--dry-run", action="store_true", help="Fetch/parse but do not write to Postgres")
    parser.add_argument("--force", action="store_true", help="Run even when outside the configured rush-hour windows")
    parser.add_argument("--input", type=Path, help="Read CSV input from a local file instead of fetching the live feed")
    parser.add_argument("--table-name", default="trip_pricing", help="Override destination table name")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds for live fetches")
    parser.add_argument("--now", help="Override current time with an ISO-8601 timestamp for testing")
    return parser


def _resolve_now(now_override: str | None, poll_tz: str) -> datetime:
    local_zone = ZoneInfo(poll_tz)
    if not now_override:
        return datetime.now(local_zone)

    parsed = datetime.fromisoformat(now_override)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_zone)
    return parsed.astimezone(local_zone)


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.input and not args.dry_run:
        parser.error("--input is only supported together with --dry-run")

    settings = Settings.from_env(require_token=args.input is None, require_database=not args.dry_run)
    now = _resolve_now(args.now, settings.poll_tz)

    if not args.force and not should_poll(now, settings.windows):
        print(f"outside poll window at {now.isoformat()}; exiting without fetch")
        return 0

    if args.input:
        csv_text = args.input.read_text()
        source_url = sanitize_source_url(settings.vdot_toll_url)
    else:
        csv_text = fetch_csv(settings.vdot_toll_url, settings.vdot_toll_token, timeout=args.timeout)
        source_url = sanitize_source_url(settings.vdot_toll_url)

    rows = parse_trip_pricing_csv(csv_text, source_url=source_url, source_tz=settings.poll_tz)
    print(
        f"parsed {len(rows)} rows from {source_url}; "
        f"interval_end_at={rows[0].interval_end_at.isoformat() if rows else 'n/a'}"
    )

    if args.dry_run:
        print("dry-run enabled; skipping database write")
        return 0

    with psycopg.connect(**settings.connection_kwargs) as conn:
        ensure_schema(conn, table_name=args.table_name)
        result = upsert_trip_pricing_rows(conn, rows, table_name=args.table_name)

    print(
        f"wrote {len(rows)} rows to {settings.pg_database}.{args.table_name} "
        f"(inserted={result.inserted}, updated={result.updated})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
