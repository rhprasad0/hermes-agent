#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${ROOT}/vendor/honcho"
PIN="952435848c45a9e797a73dbe0454e1e76cb12011"

mkdir -p "${ROOT}/vendor"
if [[ ! -d "${TARGET}/.git" ]]; then
  git clone https://github.com/plastic-labs/honcho.git "${TARGET}"
fi

git -C "${TARGET}" fetch --all --tags
git -C "${TARGET}" checkout "${PIN}"
echo "Honcho source ready at ${TARGET} (pinned to ${PIN})"
