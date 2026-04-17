# VDOT I-95/I-495 trip pricing CSV schema

This document describes the observed shape of the VDOT SmarterRoads CSV feed for Northern Virginia I-95/I-495 trip pricing.

Scope:
- feed family: `Tolling and Trip Pricing I-95 I-495`
- source format: CSV
- public metadata update rate: 10 minutes
- this repo intentionally does not store the real token or committed live payload snapshots

## Access pattern

Observed working request pattern:
- `GET https://data.511-atis-ttrip-prod.iteriscloud.com/smarterRoads/tollRoad/I95/current/tollingTripPricing_I95.csv?token=REDACTED`

Observed non-working patterns during testing:
- `Authorization: Bearer ...`
- `Authorization: ...`
- `X-Api-Key: ...`

## File quirks

Observed on a successful live fetch:
- physical line 1 is blank
- physical line 2 is the header row
- physical line 3 is a dashed separator row and must be skipped
- string fields are heavily fixed-width padded with spaces
- the separator row is not a trustworthy schema row and may not even have the same parsed column count as the header/data rows

## Canonical schema mapping

| Source column | Canonical internal name | Type | Notes |
| --- | --- | --- | --- |
| `ZONETOLLRATE` | `zone_toll_rate_usd` | numeric(10,2) | toll amount in USD |
| `ODPAIRNAME` | `od_pair_name` | text | origin/destination pair name |
| `ODPAIRID` | `od_pair_id` | integer | stable business key within a snapshot |
| `STARTZONENAME` | `start_zone_name` | text nullable | some rows are blank |
| `STARTZONEID` | `start_zone_id` | integer | always populated in sampled rows |
| `INTERVALENDDATETI` | `interval_end_at` | timestamptz | truncated source header |
| `CURRENTDATETIME` | `current_at` | timestamptz | source-local time |
| `ENDZONENAME` | `end_zone_name` | text | padded |
| `ENDZONEID` | `end_zone_id` | integer | populated in sampled rows |
| `CORRIDORN` | `corridor_name` | text | truncated source header |
| `CORRIDORID` | `corridor_id` | integer | padded in source |
| `CALULCATEDDATETIM` | `calculated_at` | timestamptz | misspelled/truncated source header |
| `LINKSTATUS` | `link_status` | text | operational status |

## Timestamp format

Observed timestamp format:
- `%d/%m/%y %H:%M:%S`
- example: `17/04/26 11:40:00`

Assumption used by the ingester:
- source timestamps are in `America/New_York`
- stored values should be normalized to UTC `timestamptz`
- raw trimmed strings should still be preserved in `raw_row`

## Observed value notes

Sample corridor values:
- `I-495-NB`
- `I-495-SB`
- `I-95-NB`
- `I-95-SB`

Sample link status values:
- `CLOSED`
- `NO_DETERMINATION`
- `NORTHBOUND_CLOSING`
- `NORTHBOUND_OPEN`

Other observed notes:
- sampled live snapshot had 317 data rows after skipping the separator row
- `ODPAIRID` values were unique within the sampled snapshot
- `STARTZONENAME` was blank for some rows, especially certain Prince William origin rows

## Parser requirements

A robust parser for this feed should:
1. ignore leading blank rows
2. parse the first nonblank row as the header
3. skip the dashed separator row even if its parsed column count is malformed
4. trim whitespace on every field and header name
5. map source headers to canonical internal names
6. fail loudly if the header row changes unexpectedly
7. treat blank `start_zone_name` as `NULL`

## Synthetic fixture policy

Tests in this repository should use synthetic data only.
Do not commit:
- real tokens
- live payload dumps
- raw logs containing authenticated URLs
