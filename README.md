# Hermes Backend

Backend foundation for Hermes.

This repo now includes the connection layer between Hermes and a self-hosted Honcho memory backend.

## What exists

- Dedicated Compose-owned PostgreSQL 16 + pgvector for Honcho
- Self-hosted Honcho on Docker Compose
- Local Codex OAuth bridge for Honcho LLM access
- Historical local backup/runbook artifacts from the earlier `pgvector-local` setup

## Current architecture

- Hermes runs on the host
- Honcho `api` + `deriver` + `redis` + `database` run via `infra/honcho/docker-compose.yml`
- Honcho uses its own Compose-managed Postgres + pgvector instance
- Honcho talks to a local `codex-bridge` service that exposes an OpenAI-compatible API backed by the current Codex OAuth login
- The bridge serves local deterministic 1536-dim embeddings because the Codex backend itself does not expose an embeddings endpoint

## Important distinction

The `honcho` package from `uv tool install honcho` is only a Procfile/process manager.
It is not the Honcho memory backend from Plastic Labs and is not part of the final architecture here.

## Current status

The Honcho stack is live.

Completed:
- Compose-owned Postgres + pgvector is running for Honcho
- codex-bridge is serving OpenAI-compatible model, chat, and embeddings endpoints
- Hermes is pointed at self-hosted Honcho and using it as the active memory provider
- cross-session recall has been validated
- nightly backup + S3 upload + restore drill have been configured for the Honcho database
- the older `pgvector-local` container, backup cron, and Docker volume were removed

## Key paths

- `infra/honcho/docker-compose.yml`
- `infra/honcho/.env.example`
- `infra/honcho/codex_bridge/`
- `docs/runbooks/honcho-memory.md`
- `docs/runbooks/codex-bridge.md`
- `scripts/fetch-honcho-source.sh`
- `scripts/honcho-smoke-test.sh`
