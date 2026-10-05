"""Protocols implemented by lower-level infrastructure and injected into services."""

from datetime import datetime
from typing import Literal, Protocol

from paybridge.types.models import RailLedgerEntry


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        ...


class Sleeper(Protocol):
    async def sleep(self, seconds: float) -> None: ...


class RandomSource(Protocol):
    def random(self) -> float:
        """Return a value in [0.0, 1.0)."""
        ...


class RailLedger(Protocol):
    def find(
        self, entry_type: Literal["PAYMENT", "REVERSAL"], payment_id: str
    ) -> RailLedgerEntry | None: ...

    def record(self, entry: RailLedgerEntry) -> RailLedgerEntry:
        """Persist the entry, or return the existing one for the same key."""
        ...


class RailAdapter(Protocol):
    async def submit(self, payment_id: str, amount_paise: int) -> RailLedgerEntry: ...

    async def reverse(self, payment_id: str, amount_paise: int) -> RailLedgerEntry: ...
