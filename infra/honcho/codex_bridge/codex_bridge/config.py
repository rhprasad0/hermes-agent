from __future__ import annotations

import os
from pathlib import Path

DEFAULT_PROVIDER_NAME = "openai-codex"
DEFAULT_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
DEFAULT_CODEX_TOKEN_URL = "https://auth.openai.com/oauth/token"
DEFAULT_CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_CODEX_CLIENT_VERSION = "1.0.0"
DEFAULT_HERMES_AUTH_PATH = Path.home() / ".hermes" / "auth.json"
DEFAULT_HERMES_AUTH_LOCK_PATH = Path.home() / ".hermes" / "auth.lock"
DEFAULT_CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
EMBEDDING_DIMENSIONS = 1536
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_MODELS = [
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-5.3-codex",
    "gpt-5.2-codex",
]


def resolve_path(env_name: str, default: Path) -> Path:
    return Path(os.environ.get(env_name, str(default))).expanduser()


def inbound_api_key() -> str | None:
    value = os.environ.get("CODEX_BRIDGE_API_KEY", "").strip()
    return value or None
