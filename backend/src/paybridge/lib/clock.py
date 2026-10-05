"""Wall-clock implementation of the Clock protocol (structural, no layer import)."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
