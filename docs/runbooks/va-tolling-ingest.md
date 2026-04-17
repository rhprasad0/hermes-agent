# VDOT I-95/I-495 toll ingester runbook

This runbook documents the local toll-pricing ingester for Northern Virginia job-search commute budgeting.

Scope:
- feed: VDOT SmarterRoads `Tolling and Trip Pricing I-95 I-495`
- corridor scope for this first version: I-95 / I-495 only
- poll cadence: every 10 minutes
- rush-hour defaults: weekdays `06:00-10:00` and `15:00-19:00` in `America/New_York`
- database target: a separate `va_tolling` database on the same Postgres instance used by the local Honcho stack (`127.0.0.1:5434`)

## Files

- `docs/schemas/va-i95-i495-trip-pricing.md`
- `config/va-tolling.env.example`
- `sql/va_tolling/001_create_role_and_database.sql`
- `sql/va_tolling/002_schema.sql`
- `scripts/run-va-toll-ingest.sh`
- `tools/va_toll_ingest/`

## Safety notes

- Keep the real VDOT token in a local env file outside the repo.
- Keep the `va_tolling_app` password in that same local env file.
- Do not commit live payloads, authenticated URLs, or logs containing query-string tokens.
- The ingester stores the sanitized source URL without the token.

## One-time setup

1. Create a local env file from `config/va-tolling.env.example`, for example:
   - `~/.config/hermes-jobs/va-tolling.env`
2. Put the real token and DB password in that local env file.
   - Quote values that contain shell-special characters, for example `VDOT_TOLL_TOKEN='...'`.
3. Create the role and database:

```bash
set -a
source infra/honcho/.env
source ~/.config/hermes-jobs/va-tolling.env
set +a
export VA_TOLLING_DB_PASSWORD="$PGPASSWORD"
PGPASSWORD="$HONCHO_DB_PASSWORD" psql -h 127.0.0.1 -p 5434 -U "$HONCHO_DB_USER" -d postgres \
  -f sql/va_tolling/001_create_role_and_database.sql
```

4. Create the table and indexes:

```bash
set -a
source ~/.config/hermes-jobs/va-tolling.env
set +a
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -f sql/va_tolling/002_schema.sql
```

## Manual validation

Dry-run against the synthetic fixture:

```bash
set -a
source ~/.config/hermes-jobs/va-tolling.env
set +a
./scripts/run-va-toll-ingest.sh --dry-run --force \
  --input tools/va_toll_ingest/tests/fixtures/i95_trip_pricing_synthetic.csv
```

Dry-run against the live feed:

```bash
set -a
source ~/.config/hermes-jobs/va-tolling.env
set +a
./scripts/run-va-toll-ingest.sh --dry-run --force
```

Live write:

```bash
set -a
source ~/.config/hermes-jobs/va-tolling.env
set +a
./scripts/run-va-toll-ingest.sh --force
```

Inspect data:

```bash
set -a
source ~/.config/hermes-jobs/va-tolling.env
set +a
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  -c "select interval_end_at, corridor_name, count(*) from trip_pricing group by 1,2 order by 1 desc,2;"
```

## Cron installation

Recommended cron entry:

```cron
*/10 * * * 1-5 mkdir -p $HOME/.local/state/va-tolling && cd /home/ryan/hermes-agent && VA_TOLLING_ENV_FILE=$HOME/.config/hermes-jobs/va-tolling.env ./scripts/run-va-toll-ingest.sh >> $HOME/.local/state/va-tolling/poller.log 2>&1
```

Why the cron line runs all weekday hours instead of encoding rush hour directly:
- the Python ingester exits cleanly outside the configured windows
- changing windows only requires editing the env file
- daylight-saving handling stays in one place

## Expected behavior

- outside configured windows: the script exits `0` after printing that it is outside the poll window
- inside configured windows with `--dry-run`: fetch + parse only, no DB writes
- inside configured windows without `--dry-run`: upsert rows into `trip_pricing`
- repeated runs in the same published interval update existing rows instead of duplicating them
