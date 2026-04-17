from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from .normalize import TripPricingRow


UPSERT_SQL = """
INSERT INTO {table_name} (
    interval_end_at,
    current_at,
    calculated_at,
    corridor_name,
    corridor_id,
    od_pair_id,
    od_pair_name,
    start_zone_id,
    start_zone_name,
    end_zone_id,
    end_zone_name,
    zone_toll_rate_usd,
    link_status,
    source_url,
    raw_row
) VALUES (
    %(interval_end_at)s,
    %(current_at)s,
    %(calculated_at)s,
    %(corridor_name)s,
    %(corridor_id)s,
    %(od_pair_id)s,
    %(od_pair_name)s,
    %(start_zone_id)s,
    %(start_zone_name)s,
    %(end_zone_id)s,
    %(end_zone_name)s,
    %(zone_toll_rate_usd)s,
    %(link_status)s,
    %(source_url)s,
    %(raw_row)s
)
ON CONFLICT (interval_end_at, od_pair_id) DO UPDATE
SET
    current_at = EXCLUDED.current_at,
    calculated_at = EXCLUDED.calculated_at,
    corridor_name = EXCLUDED.corridor_name,
    corridor_id = EXCLUDED.corridor_id,
    od_pair_name = EXCLUDED.od_pair_name,
    start_zone_id = EXCLUDED.start_zone_id,
    start_zone_name = EXCLUDED.start_zone_name,
    end_zone_id = EXCLUDED.end_zone_id,
    end_zone_name = EXCLUDED.end_zone_name,
    zone_toll_rate_usd = EXCLUDED.zone_toll_rate_usd,
    link_status = EXCLUDED.link_status,
    source_url = EXCLUDED.source_url,
    raw_row = EXCLUDED.raw_row
RETURNING xmax = 0 AS inserted
"""


@dataclass(frozen=True)
class WriteResult:
    inserted: int
    updated: int


def ensure_schema(conn: psycopg.Connection, *, table_name: str = "trip_pricing") -> None:
    table_identifier = sql.Identifier(table_name)
    corridor_index = sql.Identifier(f"{table_name}_corridor_interval_idx")
    od_pair_index = sql.Identifier(f"{table_name}_odpair_interval_idx")

    create_table = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {table_name} (
            id bigserial PRIMARY KEY,
            interval_end_at timestamptz NOT NULL,
            current_at timestamptz NOT NULL,
            calculated_at timestamptz NOT NULL,
            corridor_name text NOT NULL,
            corridor_id integer NOT NULL,
            od_pair_id integer NOT NULL,
            od_pair_name text NOT NULL,
            start_zone_id integer NOT NULL,
            start_zone_name text NULL,
            end_zone_id integer NOT NULL,
            end_zone_name text NOT NULL,
            zone_toll_rate_usd numeric(10,2) NOT NULL,
            link_status text NOT NULL,
            source_url text NOT NULL,
            raw_row jsonb NOT NULL,
            ingested_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (interval_end_at, od_pair_id)
        )
        """
    ).format(table_name=table_identifier)

    create_corridor_index = sql.SQL(
        "CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} (corridor_name, interval_end_at DESC)"
    ).format(index_name=corridor_index, table_name=table_identifier)

    create_od_pair_index = sql.SQL(
        "CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} (od_pair_id, interval_end_at DESC)"
    ).format(index_name=od_pair_index, table_name=table_identifier)

    with conn.cursor() as cur:
        cur.execute(create_table)
        cur.execute(create_corridor_index)
        cur.execute(create_od_pair_index)


def _row_to_params(row: TripPricingRow) -> dict[str, object]:
    return {
        "interval_end_at": row.interval_end_at,
        "current_at": row.current_at,
        "calculated_at": row.calculated_at,
        "corridor_name": row.corridor_name,
        "corridor_id": row.corridor_id,
        "od_pair_id": row.od_pair_id,
        "od_pair_name": row.od_pair_name,
        "start_zone_id": row.start_zone_id,
        "start_zone_name": row.start_zone_name,
        "end_zone_id": row.end_zone_id,
        "end_zone_name": row.end_zone_name,
        "zone_toll_rate_usd": row.zone_toll_rate_usd,
        "link_status": row.link_status,
        "source_url": row.source_url,
        "raw_row": Jsonb(row.raw_row),
    }


def upsert_trip_pricing_rows(
    conn: psycopg.Connection,
    rows: list[TripPricingRow],
    *,
    table_name: str = "trip_pricing",
) -> WriteResult:
    statement = sql.SQL(UPSERT_SQL).format(table_name=sql.Identifier(table_name))
    inserted = 0
    updated = 0

    with conn.transaction():
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(statement, _row_to_params(row))
                was_inserted = cur.fetchone()[0]
                if was_inserted:
                    inserted += 1
                else:
                    updated += 1

    return WriteResult(inserted=inserted, updated=updated)
