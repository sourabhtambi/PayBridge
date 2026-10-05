"""UTC and IST conversions. IST is a fixed +05:30 offset (no DST)."""

from datetime import UTC, date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def to_ist(moment: datetime) -> datetime:
    return moment.astimezone(IST)


def to_utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC)


def iso_z(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("naive datetime is not allowed")
    return to_utc(moment).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_z(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def business_date(moment: datetime) -> str:
    return to_ist(moment).date().isoformat()


def ist_day_bounds_utc(business_day: str) -> tuple[datetime, datetime]:
    """Return the [start, end) UTC interval of an IST calendar day."""
    start_ist = datetime.combine(date.fromisoformat(business_day), time.min, tzinfo=IST)
    return to_utc(start_ist), to_utc(start_ist + timedelta(days=1))
