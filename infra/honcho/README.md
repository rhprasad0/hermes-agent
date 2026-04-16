# Self-hosted Honcho on Compose-owned PostgreSQL + pgvector

This repo contains the local wiring for running Honcho as Hermes's memory backend.

What this stack does:
- runs Honcho `api`, `deriver`, `redis`, and `database` on Docker Compose
- uses a dedicated Compose-managed PostgreSQL 16 + pgvector instance for Honcho
- runs a local `codex-bridge` service that exposes an OpenAI-compatible API to Honcho
- reuses the existing Codex OAuth auth state from `~/.hermes/auth.json` and `~/.codex/auth.json`
- uses local deterministic 1536-dim embeddings inside the bridge because the Codex backend does not expose an embeddings endpoint
- includes a daily backup + Healthchecks.io + restore-tested flow for the Honcho database

Important distinction:
- `honcho` from `uv tool install honcho` is a Procfile manager and is not used here
- Plastic Labs Honcho is the memory backend/service used here

Source layout:
- `vendor/honcho/` — pinned upstream Honcho checkout used for builds
- `infra/honcho/docker-compose.yml` — local stack
- `infra/honcho/.env.example` — env template
- `infra/honcho/codex_bridge/` — local bridge package and Dockerfile

Quick start:
1. Fetch/pin upstream Honcho source:
   - `./scripts/fetch-honcho-source.sh`
2. Copy `infra/honcho/.env.example` to `infra/honcho/.env`
3. Fill in `HONCHO_DB_PASSWORD`
4. Start the stack:
   - `docker compose -f infra/honcho/docker-compose.yml up -d --build`
5. Verify:
   - `curl http://127.0.0.1:4000/health`
   - `curl http://127.0.0.1:8000/health`
   - `docker compose -f infra/honcho/docker-compose.yml logs honcho-deriver --tail 50`

Notes:
- Honcho now owns its own Compose Postgres instance exposed locally on `127.0.0.1:5434`.
- This avoids the custom Docker networking and `pg_hba.conf` hacks required when reusing the earlier `pgvector-local` container.
- The bridge enforces `CODEX_BRIDGE_API_KEY` for `/v1/*` routes when that env var is set.
- Daily backups run through `$HOME/.local/bin/honcho-nightly-backup.sh` on `30 3 * * *`; configure `HC_URL` and `S3_PREFIX` in the backup env for your own environment.
