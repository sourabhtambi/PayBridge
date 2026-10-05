"""Mock rail adapters (success mode) sharing one ledger so submits are idempotent."""

from typing import Literal

from paybridge.config.rails import RAIL_SETTINGS
from paybridge.lib.timeutil import iso_z
from paybridge.service.simulation import SimulationStore
from paybridge.types.enums import Rail
from paybridge.types.models import RailLedgerEntry
from paybridge.types.ports import Clock, RailAdapter


class InMemoryRailLedger:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], RailLedgerEntry] = {}

    def find(
        self, entry_type: Literal["PAYMENT", "REVERSAL"], payment_id: str
    ) -> RailLedgerEntry | None:
        return self._entries.get((entry_type, payment_id))

    def record(self, entry: RailLedgerEntry) -> RailLedgerEntry:
        return self._entries.setdefault((entry.type, entry.payment_id), entry)


class MockRailAdapter:
    def __init__(
        self,
        rail: Rail,
        ledger: InMemoryRailLedger,
        clock: Clock,
        sim: SimulationStore | None = None,
    ) -> None:
        self._rail = rail
        self._ledger = ledger
        self._clock = clock
        self._sim = sim

    async def _post(
        self, entry_type: Literal["PAYMENT", "REVERSAL"], payment_id: str, amount_paise: int
    ) -> RailLedgerEntry:
        if self._sim is not None:
            self._sim.check(self._rail)
        existing = self._ledger.find(entry_type, payment_id)
        if existing is not None:
            return existing
        prefix = RAIL_SETTINGS[self._rail].reference_prefix
        return self._ledger.record(
            RailLedgerEntry(
                type=entry_type,
                rail=self._rail,
                payment_id=payment_id,
                rail_ref=f"{prefix}-{entry_type[:3]}-{payment_id}",
                amount_paise=amount_paise,
                accepted_at=iso_z(self._clock.now()),
            )
        )

    async def submit(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        return await self._post("PAYMENT", payment_id, amount_paise)

    async def reverse(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        return await self._post("REVERSAL", payment_id, amount_paise)


def build_adapters(clock: Clock, sim: SimulationStore | None = None) -> dict[Rail, RailAdapter]:
    ledger = InMemoryRailLedger()
    return {rail: MockRailAdapter(rail, ledger, clock, sim) for rail in Rail}
