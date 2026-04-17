from pathlib import Path

import pytest

from va_toll_ingest.normalize import EXPECTED_SOURCE_HEADERS, parse_trip_pricing_csv


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "i95_trip_pricing_synthetic.csv"


def fixture_text() -> str:
    return FIXTURE_PATH.read_text()


def test_expected_source_headers_match_documented_order():
    assert EXPECTED_SOURCE_HEADERS == [
        "ZONETOLLRATE",
        "ODPAIRNAME",
        "ODPAIRID",
        "STARTZONENAME",
        "STARTZONEID",
        "INTERVALENDDATETI",
        "CURRENTDATETIME",
        "ENDZONENAME",
        "ENDZONEID",
        "CORRIDORN",
        "CORRIDORID",
        "CALULCATEDDATETIM",
        "LINKSTATUS",
    ]


def test_parse_trip_pricing_csv_skips_blank_and_separator_rows():
    rows = parse_trip_pricing_csv(
        fixture_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )

    assert len(rows) == 4
    assert [row.od_pair_id for row in rows] == [1000, 2000, 1122, 3100]


def test_parse_trip_pricing_csv_trims_and_maps_fields():
    first = parse_trip_pricing_csv(
        fixture_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )[0]

    assert first.zone_toll_rate_usd == 6.05
    assert first.od_pair_name == "WESTPARK (B) TO I-495 N"
    assert first.start_zone_name == "NB 495 TP Before Jones Branch (TP8NB)"
    assert first.end_zone_name == "NB 495 TP Past Route 267(TP9NB)"
    assert first.corridor_name == "I-495-NB"
    assert first.link_status == "NO_DETERMINATION"


def test_parse_trip_pricing_csv_parses_local_timestamps_to_utc():
    first = parse_trip_pricing_csv(
        fixture_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )[0]

    assert first.interval_end_at.isoformat() == "2026-04-17T15:40:00+00:00"
    assert first.current_at.isoformat() == "2026-04-17T15:35:00+00:00"
    assert first.calculated_at.isoformat() == "2026-04-17T15:30:00+00:00"


def test_parse_trip_pricing_csv_preserves_raw_row_and_blank_start_zone_name_as_none():
    third = parse_trip_pricing_csv(
        fixture_text(),
        source_url="https://example.com/tollingTripPricing_I95.csv",
        source_tz="America/New_York",
    )[2]

    assert third.start_zone_name is None
    assert third.raw_row["STARTZONENAME"] == ""
    assert third.raw_row["ODPAIRID"] == "1122"
    assert third.source_url == "https://example.com/tollingTripPricing_I95.csv"


def test_parse_trip_pricing_csv_rejects_blank_payloads():
    with pytest.raises(ValueError, match="no CSV content"):
        parse_trip_pricing_csv(
            "\n\n  \n",
            source_url="https://example.com/tollingTripPricing_I95.csv",
            source_tz="America/New_York",
        )
