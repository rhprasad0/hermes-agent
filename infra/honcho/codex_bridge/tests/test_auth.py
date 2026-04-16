from pathlib import Path

from codex_bridge.auth import (
    TokenBundle,
    load_runtime_credentials,
    resolve_runtime_credentials,
    token_is_expiring,
)


def test_load_runtime_credentials_prefers_pool_entry(tmp_path: Path) -> None:
    auth_path = tmp_path / "auth.json"
    codex_auth_path = tmp_path / "codex-auth.json"
    auth_path.write_text(
        """
        {
          "providers": {
            "openai-codex": {
              "tokens": {
                "access_token": "provider-access",
                "refresh_token": "provider-refresh"
              }
            }
          },
          "credential_pool": {
            "openai-codex": [
              {
                "access_token": "pool-access",
                "refresh_token": "pool-refresh",
                "base_url": "https://chatgpt.com/backend-api/codex",
                "auth_type": "oauth"
              }
            ]
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    codex_auth_path.write_text("{}", encoding="utf-8")

    creds = load_runtime_credentials(auth_path=auth_path, codex_auth_path=codex_auth_path)

    assert creds.access_token == "pool-access"
    assert creds.refresh_token == "pool-refresh"
    assert str(creds.base_url) == "https://chatgpt.com/backend-api/codex"


def test_load_runtime_credentials_falls_back_from_dead_pool_entry(tmp_path: Path) -> None:
    auth_path = tmp_path / "auth.json"
    codex_auth_path = tmp_path / "codex-auth.json"
    auth_path.write_text(
        """
        {
          "providers": {
            "openai-codex": {
              "tokens": {
                "access_token": "provider-access",
                "refresh_token": "provider-refresh"
              }
            }
          },
          "credential_pool": {
            "openai-codex": [
              {
                "access_token": "x.eyJleHAiOjF9.y",
                "base_url": "https://chatgpt.com/backend-api/codex",
                "auth_type": "oauth"
              }
            ]
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    codex_auth_path.write_text("{}", encoding="utf-8")

    creds = load_runtime_credentials(auth_path=auth_path, codex_auth_path=codex_auth_path)

    assert creds.access_token == "provider-access"
    assert creds.refresh_token == "provider-refresh"


def test_resolve_runtime_credentials_force_refresh_refreshes_even_if_not_expiring(tmp_path: Path, monkeypatch) -> None:
    auth_path = tmp_path / "auth.json"
    auth_lock_path = tmp_path / "auth.lock"
    codex_auth_path = tmp_path / "codex-auth.json"
    auth_path.write_text(
        """
        {
          "providers": {
            "openai-codex": {
              "tokens": {
                "access_token": "x.eyJleHAiOjk5OTk5OTk5OTl9.y",
                "refresh_token": "provider-refresh"
              }
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )
    codex_auth_path.write_text('{"tokens": {"access_token": "old", "refresh_token": "old-refresh"}}', encoding="utf-8")

    monkeypatch.setenv("CODEX_BRIDGE_HERMES_AUTH_PATH", str(auth_path))
    monkeypatch.setenv("CODEX_BRIDGE_HERMES_AUTH_LOCK_PATH", str(auth_lock_path))
    monkeypatch.setenv("CODEX_BRIDGE_CODEX_AUTH_PATH", str(codex_auth_path))

    monkeypatch.setattr(
        "codex_bridge.auth._refresh_access_token",
        lambda refresh_token, timeout_seconds: TokenBundle(
            access_token="refreshed-access",
            refresh_token="refreshed-refresh",
        ),
    )

    creds = resolve_runtime_credentials(force_refresh=True)

    assert creds.access_token == "refreshed-access"
    assert creds.refresh_token == "refreshed-refresh"


def test_token_is_expiring_detects_near_expiry() -> None:
    token = "x.eyJleHAiOjF9.y"
    assert token_is_expiring(token, now=0, skew_seconds=5) is True
