\set ON_ERROR_STOP on

CREATE TABLE IF NOT EXISTS trip_pricing (
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
);

CREATE INDEX IF NOT EXISTS trip_pricing_corridor_interval_idx
  ON trip_pricing (corridor_name, interval_end_at DESC);

CREATE INDEX IF NOT EXISTS trip_pricing_odpair_interval_idx
  ON trip_pricing (od_pair_id, interval_end_at DESC);
