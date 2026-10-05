"""Runs reconciliation for a statement date."""

from paybridge.lib.ids import new_reconciliation_id
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.service.matching import Match, match
from paybridge.types.errors import DuplicateKeyError
from paybridge.types.models import ReconciliationResult
from paybridge.types.ports import Clock


class ReconciliationService:
    def __init__(
        self, payments: PaymentsRepo, statements: StatementsRepo, recon: ReconRepo, clock: Clock
    ) -> None:
        self._payments = payments
        self._statements = statements
        self._recon = recon
        self._clock = clock

    def run(self, statement_date: str) -> list[Match]:
        payments = self._payments.list_completed_on_ist_day(statement_date)
        entries = self._statements.list_by_date(statement_date)
        matches = match(payments, entries)
        now = self._clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        for m in matches:
            try:
                self._recon.insert(_to_result(m, statement_date, now))
            except DuplicateKeyError:
                continue
        return matches


def _to_result(m: Match, statement_date: str, now: str) -> ReconciliationResult:
    p, e = m.payment, m.entry
    rail = p.rail if p else e.rail  # type: ignore[union-attr]
    return ReconciliationResult(
        id=new_reconciliation_id(),
        statement_date=statement_date,
        rail=rail,
        status=m.status,
        payment_id=p.id if p else None,
        statement_entry_id=e.id if e else None,
        payment_ref=(p.rail_reference if p else e.payment_ref),  # type: ignore[union-attr]
        payment_amount_paise=p.amount_paise if p else None,
        statement_amount_paise=e.amount_paise if e else None,
        created_at=now,
        updated_at=now,
    )
