"""Generates rail statement entries for COMPLETED payments."""

from paybridge.lib.ids import new_statement_entry_id
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.types.models import RailStatementEntry
from paybridge.types.ports import Clock


class StatementService:
    def __init__(self, payments: PaymentsRepo, statements: StatementsRepo, clock: Clock) -> None:
        self._payments = payments
        self._statements = statements
        self._clock = clock

    def generate(self, statement_date: str) -> list[RailStatementEntry]:
        now = self._clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        for p in self._payments.list_completed_on_ist_day(statement_date):
            assert p.rail_reference is not None  # DB CHECK guarantees for COMPLETED
            self._statements.insert_or_ignore(
                RailStatementEntry(
                    id=new_statement_entry_id(),
                    rail=p.rail,
                    payment_ref=p.rail_reference,
                    payment_id=p.id,
                    amount_paise=p.amount_paise,
                    statement_date=statement_date,
                    created_at=now,
                )
            )
        return self._statements.list_by_date(statement_date)
