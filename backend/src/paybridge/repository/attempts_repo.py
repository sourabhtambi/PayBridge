"""Payment attempts insert/list."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import AttemptOutcome
from paybridge.types.models import PaymentAttempt


class AttemptsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(
        self,
        payment_id: str,
        attempt_no: int,
        outcome: AttemptOutcome,
        at: str,
        error_code: str | None = None,
    ) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO payment_attempts (payment_id, attempt_no, outcome, error_code, at)"
            " VALUES (?, ?, ?, ?, ?)",
            (payment_id, attempt_no, outcome.value, error_code, at),
            "attempt number for payment",
        )

    def list_for_payment(self, payment_id: str) -> list[PaymentAttempt]:
        rows = self._conn.execute(
            "SELECT * FROM payment_attempts WHERE payment_id = ? ORDER BY attempt_no",
            (payment_id,),
        ).fetchall()
        return [
            PaymentAttempt(
                id=r["id"],
                payment_id=r["payment_id"],
                attempt_no=r["attempt_no"],
                outcome=AttemptOutcome(r["outcome"]),
                at=r["at"],
                error_code=r["error_code"],
            )
            for r in rows
        ]
