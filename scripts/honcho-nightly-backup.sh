#!/usr/bin/env bash
set -Eeuo pipefail

export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"

BACKUP_ENV_FILE="${HONCHO_BACKUP_ENV_FILE:-$HOME/.config/hermes-backups/honcho-nightly-backup.env}"
if [[ ! -f "$BACKUP_ENV_FILE" ]]; then
  echo "backup env file missing: $BACKUP_ENV_FILE" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$BACKUP_ENV_FILE"
set +a

: "${COMPOSE_ENV_FILE:?COMPOSE_ENV_FILE not set}"
if [[ ! -f "$COMPOSE_ENV_FILE" ]]; then
  echo "compose env file missing: $COMPOSE_ENV_FILE" >&2
  exit 3
fi

set -a
# shellcheck disable=SC1090
source "$COMPOSE_ENV_FILE"
set +a

required_vars=(HC_URL DB_HOST DB_PORT DB_NAME DB_USER BACKUP_DIR S3_PREFIX HONCHO_DB_PASSWORD)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "$var_name is not set" >&2
    exit 4
  fi
done

AWS_BIN="${AWS_BIN:-$(command -v aws || true)}"
CURL_BIN="${CURL_BIN:-$(command -v curl || true)}"
PG_DUMP_BIN="${PG_DUMP_BIN:-$(command -v pg_dump || true)}"
SHA256SUM_BIN="${SHA256SUM_BIN:-$(command -v sha256sum || true)}"
for bin_var in AWS_BIN CURL_BIN PG_DUMP_BIN SHA256SUM_BIN; do
  if [[ -z "${!bin_var}" ]]; then
    echo "required command not found for $bin_var" >&2
    exit 5
  fi
done

case "$S3_PREFIX" in
  */) ;;
  *) S3_PREFIX="${S3_PREFIX}/" ;;
esac

export PGPASSWORD="$HONCHO_DB_PASSWORD"

hc_ping() {
  "$CURL_BIN" -fsS -m 10 --retry 3 --retry-connrefused -o /dev/null "$1" || true
}

trap 'status=$?; hc_ping "${HC_URL}/fail"; exit "$status"' ERR

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
FILE_BASENAME="${DB_NAME}-${STAMP}"
DUMP_PATH="${BACKUP_DIR}/${FILE_BASENAME}.dump"
CHECKSUM_PATH="${DUMP_PATH}.sha256"

mkdir -p "$BACKUP_DIR"
hc_ping "${HC_URL}/start"

"$PG_DUMP_BIN" \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --format=custom \
  --file="$DUMP_PATH"

(
  cd "$BACKUP_DIR"
  "$SHA256SUM_BIN" "${FILE_BASENAME}.dump" > "${FILE_BASENAME}.dump.sha256"
)

"$AWS_BIN" s3 cp "$DUMP_PATH" "${S3_PREFIX}${FILE_BASENAME}.dump"
"$AWS_BIN" s3 cp "$CHECKSUM_PATH" "${S3_PREFIX}${FILE_BASENAME}.dump.sha256"

find "$BACKUP_DIR" -type f -name "${DB_NAME}-*.dump*" -mtime +7 -delete
hc_ping "$HC_URL"

echo "backup complete: ${FILE_BASENAME}"
