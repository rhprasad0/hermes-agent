#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE="${ROOT}/infra/honcho/docker-compose.yml"
ENV_FILE="${ROOT}/infra/honcho/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file: $ENV_FILE" >&2
  exit 2
fi

api_key_line="$(grep -E '^CODEX_BRIDGE_API_KEY=' "$ENV_FILE" | tail -n1 || true)"
API_KEY="${api_key_line#*=}"
API_KEY="${API_KEY%\"}"
API_KEY="${API_KEY#\"}"
if [[ -z "$API_KEY" ]]; then
  echo "missing CODEX_BRIDGE_API_KEY in $ENV_FILE" >&2
  exit 3
fi

curl -fsS http://127.0.0.1:4000/health >/dev/null
curl -fsS http://127.0.0.1:8000/health >/dev/null
curl -fsS -H "Authorization: Bearer ${API_KEY}" http://127.0.0.1:4000/v1/models >/dev/null

docker compose -f "$COMPOSE" ps

echo "Bridge, Honcho API, and bridge auth route health checks passed."
