from __future__ import annotations

import base64
import copy
import fcntl
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import httpx

from codex_bridge.config import (
    DEFAULT_CODEX_AUTH_PATH,
    DEFAULT_CODEX_BASE_URL,
    DEFAULT_CODEX_CLIENT_ID,
    DEFAULT_CODEX_TOKEN_URL,
    DEFAULT_HERMES_AUTH_LOCK_PATH,
    DEFAULT_HERMES_AUTH_PATH,
    DEFAULT_PROVIDER_NAME,
    resolve_path,
)


@dataclass(frozen=True)
class RuntimeCredentials:
    access_token: str
    refresh_token: str | None = None
    base_url: str = DEFAULT_CODEX_BASE_URL
    auth_type: str = "oauth"
    source: str = DEFAULT_PROVIDER_NAME
    pool_index: int | None = None


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str


def resolve_runtime_credentials(*, force_refresh: bool = False, skew_seconds: int = 300) -> RuntimeCredentials:
    auth_path, auth_lock_path, codex_auth_path = _runtime_paths()
    creds = load_runtime_credentials(auth_path=auth_path, codex_auth_path=codex_auth_path)
    should_refresh = force_refresh or (creds.refresh_token and token_is_expiring(creds.access_token, skew_seconds=skew_seconds))
    if should_refresh:
        creds = refresh_runtime_credentials(
            creds,
            auth_path=auth_path,
            auth_lock_path=auth_lock_path,
            codex_auth_path=codex_auth_path,
            force=force_refresh,
        )
    return creds


def load_runtime_credentials(
    auth_path: Path = DEFAULT_HERMES_AUTH_PATH,
    codex_auth_path: Path = DEFAULT_CODEX_AUTH_PATH,
) -> RuntimeCredentials:
    hermes_auth = _read_json(auth_path)
    pool_entry, pool_index = _select_pool_entry(hermes_auth)
    if pool_entry is not None:
        return _build_credentials(pool_entry, source=f"{auth_path}:credential_pool", pool_index=pool_index)

    provider_tokens = _select_provider_tokens(hermes_auth)
    if provider_tokens is not None:
        return _build_credentials(provider_tokens, source=f"{auth_path}:providers")

    codex_auth = _read_json(codex_auth_path)
    codex_tokens = _select_codex_tokens(codex_auth)
    if codex_tokens is not None:
        return _build_credentials(codex_tokens, source=f"{codex_auth_path}:tokens")

    raise ValueError("No Codex OAuth credentials found.")


def refresh_runtime_credentials(
    creds: RuntimeCredentials,
    *,
    auth_path: Path,
    auth_lock_path: Path,
    codex_auth_path: Path,
    timeout_seconds: float = 20.0,
    force: bool = False,
) -> RuntimeCredentials:
    if not creds.refresh_token:
        return creds

    auth_lock_path.parent.mkdir(parents=True, exist_ok=True)
    with auth_lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)

        current = load_runtime_credentials(auth_path=auth_path, codex_auth_path=codex_auth_path)
        if not force and not token_is_expiring(current.access_token):
            return current
        if not current.refresh_token:
            return current

        bundle = _refresh_access_token(current.refresh_token, timeout_seconds=timeout_seconds)
        _persist_tokens(
            bundle,
            auth_path=auth_path,
            codex_auth_path=codex_auth_path,
            pool_index=current.pool_index,
            base_url=current.base_url,
            auth_type=current.auth_type,
        )
        return RuntimeCredentials(
            access_token=bundle.access_token,
            refresh_token=bundle.refresh_token,
            base_url=current.base_url,
            auth_type=current.auth_type,
            source=current.source,
            pool_index=current.pool_index,
        )


def token_is_expiring(token: str | None, now: float | None = None, skew_seconds: int = 300) -> bool:
    if not token:
        return True

    parts = token.split(".")
    if len(parts) < 2:
        return True

    payload = _decode_jwt_payload(parts[1])
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return True

    current_time = time.time() if now is None else now
    return float(exp) <= float(current_time) + float(skew_seconds)


def _refresh_access_token(refresh_token: str, *, timeout_seconds: float) -> TokenBundle:
    response = httpx.post(
        DEFAULT_CODEX_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": DEFAULT_CODEX_CLIENT_ID,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = _string_or_none(payload.get("access_token"))
    next_refresh = _string_or_none(payload.get("refresh_token"))
    if not access_token or not next_refresh:
        raise ValueError("Refresh response did not include access_token and refresh_token.")
    return TokenBundle(access_token=access_token, refresh_token=next_refresh)


def _persist_tokens(
    bundle: TokenBundle,
    *,
    auth_path: Path,
    codex_auth_path: Path,
    pool_index: int | None,
    base_url: str,
    auth_type: str,
) -> None:
    _persist_hermes_auth(
        bundle,
        auth_path=auth_path,
        pool_index=pool_index,
        base_url=base_url,
        auth_type=auth_type,
    )
    _persist_codex_auth(bundle, codex_auth_path=codex_auth_path)


def _persist_hermes_auth(
    bundle: TokenBundle,
    *,
    auth_path: Path,
    pool_index: int | None,
    base_url: str,
    auth_type: str,
) -> None:
    document = _read_json(auth_path)

    providers = document.setdefault("providers", {})
    if isinstance(providers, dict):
        provider_state = providers.setdefault(DEFAULT_PROVIDER_NAME, {})
        if isinstance(provider_state, dict):
            tokens = provider_state.setdefault("tokens", {})
            if isinstance(tokens, dict):
                tokens["access_token"] = bundle.access_token
                tokens["refresh_token"] = bundle.refresh_token
            provider_state.setdefault("auth_mode", "chatgpt")
            provider_state["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    credential_pool = document.setdefault("credential_pool", {})
    if isinstance(credential_pool, dict):
        entries = credential_pool.setdefault(DEFAULT_PROVIDER_NAME, [])
        if isinstance(entries, list):
            targets: list[dict[str, Any]] = []
            if pool_index is not None and 0 <= pool_index < len(entries) and isinstance(entries[pool_index], dict):
                targets.append(entries[pool_index])
            else:
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("auth_type") == "oauth":
                        targets.append(entry)
            for entry in targets:
                entry["access_token"] = bundle.access_token
                entry["refresh_token"] = bundle.refresh_token
                entry["base_url"] = base_url
                entry["auth_type"] = auth_type
                entry["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    auth_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(auth_path, document)


def _persist_codex_auth(bundle: TokenBundle, *, codex_auth_path: Path) -> None:
    document = _read_json(codex_auth_path)
    tokens = document.get("tokens") if isinstance(document, dict) else None
    if not isinstance(tokens, dict):
        tokens = {}
        document["tokens"] = tokens
    tokens["access_token"] = bundle.access_token
    tokens["refresh_token"] = bundle.refresh_token
    codex_auth_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(codex_auth_path, document)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        tmp_path = Path(handle.name)
    os.replace(tmp_path, path)


def _build_credentials(payload: Mapping[str, Any], *, source: str, pool_index: int | None = None) -> RuntimeCredentials:
    access_token = _string_or_none(payload.get("access_token"))
    if not access_token:
        raise ValueError("Credential payload is missing an access token.")

    refresh_token = _string_or_none(payload.get("refresh_token"))
    base_url = _string_or_none(payload.get("base_url")) or DEFAULT_CODEX_BASE_URL
    auth_type = _string_or_none(payload.get("auth_type")) or "oauth"
    return RuntimeCredentials(
        access_token=access_token,
        refresh_token=refresh_token,
        base_url=base_url,
        auth_type=auth_type,
        source=source,
        pool_index=pool_index,
    )


def _select_pool_entry(document: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, int | None]:
    credential_pool = document.get("credential_pool")
    if not isinstance(credential_pool, Mapping):
        return None, None

    entries = credential_pool.get(DEFAULT_PROVIDER_NAME)
    if not isinstance(entries, list):
        return None, None

    refreshable_fallback: tuple[Mapping[str, Any], int] | None = None
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            continue
        access_token = _string_or_none(entry.get("access_token"))
        refresh_token = _string_or_none(entry.get("refresh_token"))
        if not access_token:
            continue
        if refresh_token and refreshable_fallback is None:
            refreshable_fallback = (entry, index)
        if not token_is_expiring(access_token):
            return entry, index
    return refreshable_fallback or (None, None)


def _select_provider_tokens(document: Mapping[str, Any]) -> Mapping[str, Any] | None:
    providers = document.get("providers")
    if not isinstance(providers, Mapping):
        return None

    provider = providers.get(DEFAULT_PROVIDER_NAME)
    if not isinstance(provider, Mapping):
        return None

    tokens = provider.get("tokens")
    if not isinstance(tokens, Mapping):
        return None
    if not _string_or_none(tokens.get("access_token")):
        return None
    return tokens


def _select_codex_tokens(document: Mapping[str, Any]) -> Mapping[str, Any] | None:
    tokens = document.get("tokens") if isinstance(document, Mapping) else None
    if isinstance(tokens, Mapping) and _string_or_none(tokens.get("access_token")):
        return tokens
    if _string_or_none(document.get("access_token")):
        return document
    return None


def _runtime_paths() -> tuple[Path, Path, Path]:
    return (
        resolve_path("CODEX_BRIDGE_HERMES_AUTH_PATH", DEFAULT_HERMES_AUTH_PATH),
        resolve_path("CODEX_BRIDGE_HERMES_AUTH_LOCK_PATH", DEFAULT_HERMES_AUTH_LOCK_PATH),
        resolve_path("CODEX_BRIDGE_CODEX_AUTH_PATH", DEFAULT_CODEX_AUTH_PATH),
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}
    loaded = json.loads(content)
    return copy.deepcopy(loaded) if isinstance(loaded, dict) else {}


def _decode_jwt_payload(payload_b64: str) -> dict[str, Any]:
    padding = "=" * (-len(payload_b64) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
