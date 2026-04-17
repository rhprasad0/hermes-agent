#!/usr/bin/env bash
set -Eeuo pipefail

export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${VA_TOLLING_ENV_FILE:-$HOME/.config/hermes-jobs/va-tolling.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing va-tolling env file: $ENV_FILE" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec uv run --project "$ROOT/tools/va_toll_ingest" \
  python -m va_toll_ingest.main "$@"
