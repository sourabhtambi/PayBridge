"""Fires the settlement run once per IST business day at 23:59 IST."""

from collections.abc import Callable
from datetime import datetime, time, timedelta

from paybridge.lib.timeutil import IST, business_date, to_ist
from paybridge.types.ports import Clock

RUN_TIME = time(23, 59)


def next_run(now: datetime) -> datetime:
    """Next 23:59 Asia/Kolkata strictly after now, as an IST-aware datetime."""
    local = to_ist(now)
    today = datetime.combine(local.date(), RUN_TIME, tzinfo=IST)
    return today if local < today else today + timedelta(days=1)


class SettlementScheduler:
    def __init__(self, clock: Clock, run: Callable[[str], object]) -> None:
        self._clock = clock
        self._run = run
        self._next = next_run(clock.now())

    def tick(self) -> bool:
        """Run for the current business date if the scheduled time has passed."""
        now = self._clock.now()
        if now < self._next:
            return False
        self._run(business_date(self._next))
        self._next = next_run(now)
        return True
