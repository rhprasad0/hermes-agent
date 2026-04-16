# Honcho memory runbook

This runbook captures the local self-hosted Hermes memory stack.

Architecture:
- Hermes runs on the host
- Honcho `api`, `deriver`, `redis`, and `database` run on Docker Compose
- Honcho uses its own Compose-managed PostgreSQL 16 + pgvector instance
- Honcho talks to the local bridge through `http://codex-bridge:8001/v1`
- Hermes talks to Honcho through `http://127.0.0.1:8000`

Why the bridge exists:
- Hermes currently authenticates to Codex with OAuth tokens stored in `~/.hermes/auth.json` / `~/.codex/auth.json`
- Honcho expects an OpenAI-compatible base URL + API key
- The bridge converts Honcho's OpenAI-compatible chat requests into Codex Responses API calls
- The Codex backend does not provide an embeddings endpoint, so the bridge also serves deterministic local 1536-dim embeddings

Important distinction:
- `uv tool install honcho` installs the Procfile manager and is not part of this stack
- this stack uses Plastic Labs Honcho from `vendor/honcho/`

Files:
- `infra/honcho/docker-compose.yml`
- `infra/honcho/.env`
- `infra/honcho/.env.example`
- `infra/honcho/codex_bridge/`
- `scripts/fetch-honcho-source.sh`
- `scripts/honcho-smoke-test.sh`

Prerequisites:
- `~/.hermes/auth.json` and `~/.codex/auth.json` exist and contain working Codex OAuth credentials
- `vendor/honcho/` exists at the pinned upstream commit

Bring-up:
1. Copy `infra/honcho/.env.example` to `infra/honcho/.env`
2. Fill in `HONCHO_DB_PASSWORD`
3. Ensure `HERMES_AUTH_PATH`, `HERMES_AUTH_LOCK_PATH`, and `CODEX_AUTH_PATH` point at the local host auth files
4. Start:
   - `docker compose -f infra/honcho/docker-compose.yml up -d --build`
5. Verify:
   - `curl http://127.0.0.1:4000/health`
   - `curl http://127.0.0.1:8000/health`
   - `docker compose -f infra/honcho/docker-compose.yml logs honcho-deriver --tail 50`

Expected ports:
- bridge: `127.0.0.1:4000`
- Honcho API: `127.0.0.1:8000`
- Honcho Postgres: `127.0.0.1:5434`
- Redis: `127.0.0.1:6379`

Hermes wiring:
- set `memory.provider: honcho` in `~/.hermes/config.yaml`
- configure Honcho local base URL in `~/.hermes/honcho.json` or `~/.honcho/config.json`
- self-hosted local mode should use the local Honcho API instead of cloud

Smoke checks:
- `scripts/honcho-smoke-test.sh`
- `hermes memory status`
- `hermes doctor`

Limitations right now:
- bridge streaming `/v1/chat/completions` is not implemented yet
- bridge embeddings are deterministic local hashed vectors, not vendor semantic embeddings
- bridge relies on mounted host OAuth state; if Codex login expires, refresh must succeed through the mounted auth files

Backup scope:
- durable: the Compose-owned Honcho Postgres volume/database
- disposable: Redis cache and bridge process state

Backup implementation:
- script: `$HOME/.local/bin/honcho-nightly-backup.sh`
- local backup config: `$HOME/.config/hermes-backups/honcho-nightly-backup.env`
- local backup directory: `$HOME/.local/state/honcho-backups/`
- cron: `30 3 * * * $HOME/.local/bin/honcho-nightly-backup.sh >> $HOME/.local/state/honcho-backups/backup.log 2>&1`
- Healthchecks.io URL: configure `HC_URL` in the backup env, for example `https://hc-ping.com/<uuid>`
- S3 prefix: configure `S3_PREFIX` in the backup env, for example `s3://<bucket>/postgres-nightly-backups/<host>/honcho-compose/honcho/`

Restore drill target:
- restore `honcho` into `honcho_restore`
- latest verified restore drill succeeded

Legacy cleanup:
- the earlier `pgvector-local` container, nightly backup cron, and `pgvector-local-data` volume were removed during the pivot
