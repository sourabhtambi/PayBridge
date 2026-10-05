"""Pure matching of COMPLETED payments against rail statement entries."""

from dataclasses import dataclass

from paybridge.types.enums import ReconStatus
from paybridge.types.models import Payment, RailStatementEntry


@dataclass(frozen=True)
class Match:
    status: ReconStatus
    payment: Payment | None
    entry: RailStatementEntry | None


def match(payments: list[Payment], entries: list[RailStatementEntry]) -> list[Match]:
    """Match on payment id, rail reference and exact paise amount."""
    by_payment = {e.payment_id: e for e in entries if e.payment_id is not None}
    used: set[str] = set()
    out: list[Match] = []
    for p in payments:
        e = by_payment.get(p.id)
        if e is None or e.rail != p.rail or e.payment_ref != p.rail_reference:
            out.append(Match(ReconStatus.UNMATCHED_INTERNAL, p, None))
            continue
        used.add(e.id)
        status = (
            ReconStatus.MATCHED if e.amount_paise == p.amount_paise else ReconStatus.AMOUNT_MISMATCH
        )
        out.append(Match(status, p, e))
    out.extend(Match(ReconStatus.UNMATCHED_EXTERNAL, None, e) for e in entries if e.id not in used)
    return out
