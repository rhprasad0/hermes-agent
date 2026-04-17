import os
import uuid
from pathlib import Path

import pytest
import psycopg

from va_toll_ingest.db import UPSERT_SQL, ensure_schema, upsert_trip_pricing_rows
from va_toll_ingest.normalize import parse_trip_pricing_csv


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "i95_trip_pricing_synthetic.csv"


def test_upsert_sql_targets_interval_and_od_pair_conflict_key():
    assert "ON CONFLICT (interval_end_at, od_pair_id)" in UPSERT_SQL
    assert "raw_row = EXCLUDED.raw_row" in UPSERT_SQL


@pytest.mark.skipif("VA_TOLL_TEST_DSN" not in os.environ, reason="requires Postgres test DSN")
def test_upsert_trip_pricing_rows_is_idempotent():
    rows = parse_trip_pricing_csv(
        FIXTURE_PATH.read_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )
    table_name = f"trip_pricing_test_{uuid.uuid4().hex[:8]}"

    with psycopg.connect(os.environ["VA_TOLL_TEST_DSN"]) as conn:
        ensure_schema(conn, table_name=table_name)
        first = upsert_trip_pricing_rows(conn, rows, table_name=table_name)
        second = upsert_trip_pricing_rows(conn, rows, table_name=table_name)
        conn.commit()

    with psycopg.connect(os.environ["VA_TOLL_TEST_DSN"]) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            cur.execute(f"SELECT start_zone_name FROM {table_name} WHERE od_pair_id = 1122")
            start_zone_name = cur.fetchone()[0]
            cur.execute(f"DROP TABLE {table_name}")
            conn.commit()

    assert first.inserted == 4
    assert first.updated == 0
    assert second.inserted == 0
    assert second.updated == 4
    assert count == 4
    assert start_zone_name is None


@pytest.mark.skipif("VA_TOLL_TEST_DSN" not in os.environ, reason="requires Postgres test DSN")
def test_upsert_trip_pricing_rows_rolls_back_partial_batch_on_error():
    rows = parse_trip_pricing_csv(
        FIXTURE_PATH.read_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )
    table_name = f"trip_pricing_test_{uuid.uuid4().hex[:8]}"
    bad_row = rows[1].__class__(
        interval_end_at=rows[1].interval_end_at,
        current_at=rows[1].current_at,
        calculated_at=rows[1].calculated_at,
        corridor_name=rows[1].corridor_name,
        corridor_id="not-an-integer",
        od_pair_id=rows[1].od_pair_id,
        od_pair_name=rows[1].od_pair_name,
        start_zone_id=rows[1].start_zone_id,
        start_zone_name=rows[1].start_zone_name,
        end_zone_id=rows[1].end_zone_id,
        end_zone_name=rows[1].end_zone_name,
        zone_toll_rate_usd=rows[1].zone_toll_rate_usd,
        link_status=rows[1].link_status,
        source_url=rows[1].source_url,
        raw_row=rows[1].raw_row,
    )

    with pytest.raises(psycopg.Error):
        with psycopg.connect(os.environ["VA_TOLL_TEST_DSN"], autocommit=True) as conn:
            ensure_schema(conn, table_name=table_name)
            upsert_trip_pricing_rows(conn, [rows[0], bad_row], table_name=table_name)

    with psycopg.connect(os.environ["VA_TOLL_TEST_DSN"]) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            cur.execute(f"DROP TABLE {table_name}")
            conn.commit()

    assert count == 0
