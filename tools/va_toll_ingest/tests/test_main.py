from pathlib import Path

import pytest

from va_toll_ingest.main import main


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "i95_trip_pricing_synthetic.csv"


def test_main_rejects_input_without_dry_run():
    with pytest.raises(SystemExit) as excinfo:
        main(["--input", str(FIXTURE_PATH), "--force"])

    assert excinfo.value.code == 2
