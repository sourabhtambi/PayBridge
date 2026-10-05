from datetime import UTC, datetime, timedelta, timezone

import pytest

from paybridge.lib.timeutil import (
    business_date,
    iso_z,
    ist_day_bounds_utc,
    parse_iso_z,
    to_ist,
    to_utc,
)


def test_iso_z_format() -> None:
    assert iso_z(datetime(2026, 10, 4, 9, 30, 0, 999, tzinfo=UTC)) == "2026-10-04T09:30:00Z"


def test_iso_z_converts_other_zones() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    assert iso_z(datetime(2026, 10, 4, 15, 0, tzinfo=ist)) == "2026-10-04T09:30:00Z"


def test_iso_z_rejects_naive() -> None:
    with pytest.raises(ValueError):
        iso_z(datetime(2026, 10, 4))


def test_parse_iso_z_round_trip() -> None:
    assert parse_iso_z("2026-10-04T09:30:00Z") == datetime(2026, 10, 4, 9, 30, tzinfo=UTC)


def test_to_ist_and_back() -> None:
    utc = datetime(2026, 10, 4, 9, 30, tzinfo=UTC)
    ist = to_ist(utc)
    assert (ist.hour, ist.minute) == (15, 0)
    assert to_utc(ist) == utc


def test_business_date_ist_boundaries() -> None:
    assert business_date(datetime(2026, 10, 4, 18, 29, 59, tzinfo=UTC)) == "2026-10-04"
    assert business_date(datetime(2026, 10, 4, 18, 30, 0, tzinfo=UTC)) == "2026-10-05"
    assert business_date(datetime(2026, 10, 4, 0, 0, tzinfo=UTC)) == "2026-10-04"


def test_ist_day_bounds_utc() -> None:
    start, end = ist_day_bounds_utc("2026-10-04")
    assert start == datetime(2026, 10, 3, 18, 30, tzinfo=UTC)
    assert end == datetime(2026, 10, 4, 18, 30, tzinfo=UTC)
    assert business_date(start) == "2026-10-04"
    assert business_date(end - timedelta(seconds=1)) == "2026-10-04"
    assert business_date(end) == "2026-10-05"
