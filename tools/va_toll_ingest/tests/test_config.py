from va_toll_ingest.config import Settings
from va_toll_ingest.time_windows import parse_window


def test_connection_kwargs_preserve_password_without_conninfo_parsing():
    settings = Settings(
        vdot_toll_url="https://example.com/feed.csv",
        vdot_toll_token="token",
        pg_host="127.0.0.1",
        pg_port=5434,
        pg_database="va_tolling",
        pg_user="va_tolling_app",
        pg_password=r"space slash\\ value",
        poll_tz="America/New_York",
        am_window=parse_window("06:00-10:00"),
        pm_window=parse_window("15:00-19:00"),
    )

    assert settings.connection_kwargs == {
        "host": "127.0.0.1",
        "port": 5434,
        "dbname": "va_tolling",
        "user": "va_tolling_app",
        "password": r"space slash\\ value",
    }
