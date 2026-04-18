from datetime import date

from ynab_mcp.config import Settings, normalize_month


def test_settings_loads_values_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "ynab.env"
    env_file.write_text(
        "YNAB_ACCESS_TOKEN=test-token\n"
        "YNAB_PLAN_ID=budget-plan\n"
        "YNAB_BASE_URL=https://api.ynab.example/v1\n"
    )
    monkeypatch.setenv("YNAB_ENV_FILE", str(env_file))

    settings = Settings.from_env()

    assert settings.access_token == "test-token"
    assert settings.plan_id == "budget-plan"
    assert settings.base_url == "https://api.ynab.example/v1"


def test_normalize_month_accepts_current_year_month_and_full_date():
    today = date(2026, 4, 18)

    assert normalize_month("current", today=today) == "2026-04-01"
    assert normalize_month("2026-04", today=today) == "2026-04-01"
    assert normalize_month("2026-04-18", today=today) == "2026-04-18"
