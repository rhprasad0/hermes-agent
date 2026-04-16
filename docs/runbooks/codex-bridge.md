# Codex bridge runbook

Purpose:
- expose a local OpenAI-compatible API for Honcho
- reuse the existing host Codex OAuth login
- translate OpenAI chat-completions style requests into Codex Responses API calls
- provide a local embeddings endpoint because Codex does not expose `/v1/embeddings`

Current endpoints:
- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/embeddings`

Auth model:
- inbound Honcho -> bridge auth uses `CODEX_BRIDGE_API_KEY`
- bridge -> Codex auth uses mounted host OAuth files:
  - `~/.hermes/auth.json`
  - `~/.hermes/auth.lock`
  - `~/.codex/auth.json`

Mounted container paths:
- `/run/hermes/auth.json`
- `/run/hermes/auth.lock`
- `/run/codex/auth.json`

Key behavior:
- `/v1/chat/completions` accepts OpenAI-style requests and turns them into Codex Responses API calls
- JSON mode is guided by injected instructions
- tool calls are translated between OpenAI chat-completions shape and Codex Responses shape
- `/v1/embeddings` returns deterministic 1536-dim local vectors

Known limitations:
- chat streaming is not implemented yet
- embeddings are lexical/hash-based, not vendor semantic embeddings
- strict JSON-schema enforcement is best-effort and currently relies primarily on model instruction-following

Runtime package path:
- `infra/honcho/codex_bridge/`

Local test command:
- `cd infra/honcho/codex_bridge && uv run pytest -q`

Quick manual bridge probe:
- `cd infra/honcho/codex_bridge && uv run python - <<'PY' ... PY`
- or after compose bring-up:
  - `curl http://127.0.0.1:4000/health`
