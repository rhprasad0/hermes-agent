from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import sanitize_source_url


EXPECTED_SOURCE_HEADERS = [
    "ZONETOLLRATE",
    "ODPAIRNAME",
    "ODPAIRID",
    "STARTZONENAME",
    "STARTZONEID",
    "INTERVALENDDATETI",
    "CURRENTDATETIME",
    "ENDZONENAME",
    "ENDZONEID",
    "CORRIDORN",
    "CORRIDORID",
    "CALULCATEDDATETIM",
    "LINKSTATUS",
]


@dataclass(frozen=True)
class TripPricingRow:
    interval_end_at: datetime
    current_at: datetime
    calculated_at: datetime
    corridor_name: str
    corridor_id: int
    od_pair_id: int
    od_pair_name: str
    start_zone_id: int
    start_zone_name: str | None
    end_zone_id: int
    end_zone_name: str
    zone_toll_rate_usd: float
    link_status: str
    source_url: str
    raw_row: dict[str, str]


def _normalize_header_cell(cell: str) -> str:
    return cell.strip()


def _trim_row(row: list[str]) -> list[str]:
    return [cell.strip() for cell in row]


def _is_blank_row(row: list[str]) -> bool:
    return not row or all(not cell.strip() for cell in row)


def _is_separator_row(row: list[str]) -> bool:
    tokens = [cell.strip() for cell in row if cell.strip()]
    return bool(tokens) and all(set(token) <= {"-", "."} for token in tokens)


def _parse_timestamp(value: str, source_tz: str) -> datetime:
    local_zone = ZoneInfo(source_tz)
    local_time = datetime.strptime(value, "%d/%m/%y %H:%M:%S")
    return local_time.replace(tzinfo=local_zone).astimezone(ZoneInfo("UTC"))


def parse_trip_pricing_csv(text: str, *, source_url: str, source_tz: str) -> list[TripPricingRow]:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    while rows and _is_blank_row(rows[0]):
        rows.pop(0)

    if not rows:
        raise ValueError("no CSV content after trimming blank lines")

    header = [_normalize_header_cell(cell) for cell in rows.pop(0)]
    if header != EXPECTED_SOURCE_HEADERS:
        raise ValueError(f"unexpected CSV header: {header}")

    parsed_rows: list[TripPricingRow] = []
    cleaned_source_url = sanitize_source_url(source_url)

    for row in rows:
        if _is_blank_row(row) or _is_separator_row(row):
            continue
        if len(row) != len(header):
            raise ValueError(f"unexpected column count {len(row)} for row: {row}")

        trimmed = _trim_row(row)
        raw_row = dict(zip(header, trimmed, strict=True))
        start_zone_name = raw_row["STARTZONENAME"] or None

        parsed_rows.append(
            TripPricingRow(
                interval_end_at=_parse_timestamp(raw_row["INTERVALENDDATETI"], source_tz),
                current_at=_parse_timestamp(raw_row["CURRENTDATETIME"], source_tz),
                calculated_at=_parse_timestamp(raw_row["CALULCATEDDATETIM"], source_tz),
                corridor_name=raw_row["CORRIDORN"],
                corridor_id=int(raw_row["CORRIDORID"]),
                od_pair_id=int(raw_row["ODPAIRID"]),
                od_pair_name=raw_row["ODPAIRNAME"],
                start_zone_id=int(raw_row["STARTZONEID"]),
                start_zone_name=start_zone_name,
                end_zone_id=int(raw_row["ENDZONEID"]),
                end_zone_name=raw_row["ENDZONENAME"],
                zone_toll_rate_usd=float(raw_row["ZONETOLLRATE"]),
                link_status=raw_row["LINKSTATUS"],
                source_url=cleaned_source_url,
                raw_row=raw_row,
            )
        )

    if not parsed_rows:
        raise ValueError("no data rows parsed from CSV")

    return parsed_rows
