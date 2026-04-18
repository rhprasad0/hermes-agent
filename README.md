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

## Slack channel isolation with Honcho

This install also supports Slack channels with their own prompt, session behavior, and Honcho memory scope.

Current pattern:
- keep Hermes source changes in `~/.hermes/hermes-agent`
- keep live operator config in `~/.hermes/config.yaml`
- keep Honcho memory provider config in `~/.hermes/honcho.json`
- use one Honcho workspace, but scope peers/sessions by gateway metadata instead of creating one Honcho workspace per Slack channel

For a shared-room Slack channel such as `#budget`, the local config can combine three layers:

1. Channel prompt in `~/.hermes/config.yaml`
2. Shared session override for just that Slack channel
3. Channel-scoped Honcho peer/assistant memory in `~/.hermes/honcho.json`

Example local config:

```yaml
slack:
  channel_prompts:
    C_BUDGET_CHANNEL_ID: |
      You are Hermes in the #budget Slack channel.
      Treat this room as a shared budgeting workspace.
      Prefer explicit assumptions, simple arithmetic, and actionable next steps.
  shared_session_channels:
    - C_BUDGET_CHANNEL_ID
  free_response_channels:
    - C_BUDGET_CHANNEL_ID

group_sessions_per_user: true
thread_sessions_per_user: false
```

```json
{
  "enabled": true,
  "workspace": "hermes-local",
  "gatewayPeerScope": "channel",
  "gatewayAssistantScope": "channel",
  "gatewayScopeIncludeWorkspace": true
}
```

What this does:
- `channel_prompts` gives the room its own operating instructions
- `shared_session_channels` makes top-level conversation state shared for that Slack channel without changing every other channel
- `free_response_channels` lets Hermes answer in that room without requiring `@mention`
- `group_sessions_per_user: true` preserves per-user isolation everywhere else by default
- `thread_sessions_per_user: false` keeps Slack threads shared by default
- channel-scoped Honcho settings keep long-term memory from bleeding across channels or workspaces

Operational note:
- `~/.hermes/*` is local machine state and is not tracked in this repo
- after changing local Hermes config or gateway code, restart the gateway service so Slack picks up the new behavior

## YNAB budget channel integration

This repo also includes a small YNAB MCP server for the Slack budget channel workflow.

Pattern:
- keep the real YNAB token in a local file such as `~/.config/hermes-ynab/ynab.env`
- register the MCP server from `tools/ynab_mcp/` in `~/.hermes/config.yaml`
- point the budget channel prompt at the YNAB MCP tools
- use the same YNAB MCP tools for both read workflows and explicit write requests in the budget channel
- use a YOLO-lite policy for explicit writes: execute clearly worded requests directly, ask only when matching is ambiguous or the intended change is unclear
- keep Honcho memory channel-scoped so budget-channel memory stays in the budget channel

See:
- `tools/ynab_mcp/README.md`
- `config/ynab.env.example`
- `docs/runbooks/ynab-budget-channel.md`
- `docs/runbooks/hermes-chat-abort-honcho-prefetch.md`

## Key paths

- `infra/honcho/docker-compose.yml`
- `infra/honcho/.env.example`
- `infra/honcho/codex_bridge/`
- `docs/runbooks/honcho-memory.md`
- `docs/runbooks/codex-bridge.md`
- `docs/runbooks/slack-channel-isolation-honcho.md`
- `docs/runbooks/ynab-budget-channel.md`
- `docs/runbooks/hermes-chat-abort-honcho-prefetch.md`
- `docs/runbooks/va-tolling-ingest.md`
- `docs/schemas/va-i95-i495-trip-pricing.md`
- `config/ynab.env.example`
- `tools/ynab_mcp/`
- `scripts/fetch-honcho-source.sh`
- `scripts/honcho-smoke-test.sh`
