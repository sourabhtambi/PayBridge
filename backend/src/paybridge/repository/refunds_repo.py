"""Refund persistence."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import RefundState
from paybridge.types.models import Refund


def _to_refund(row: sqlite3.Row) -> Refund:
    return Refund(
        id=row["id"],
        payment_id=row["payment_id"],
        amount_paise=row["amount_paise"],
        state=RefundState(row["state"]),
        requested_by=row["requested_by"],
        decided_by=row["decided_by"],
        reason_code=row["reason_code"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class RefundsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, r: Refund) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO refunds (id, payment_id, amount_paise, state, requested_by, decided_by,"
            " reason_code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.id,
                r.payment_id,
                r.amount_paise,
                r.state.value,
                r.requested_by,
                r.decided_by,
                r.reason_code,
                r.created_at,
                r.updated_at,
            ),
            "refund for payment",
        )

    def get(self, refund_id: str) -> Refund | None:
        row = self._conn.execute("SELECT * FROM refunds WHERE id = ?", (refund_id,)).fetchone()
        return _to_refund(row) if row else None

    def get_for_payment(self, payment_id: str) -> Refund | None:
        row = self._conn.execute(
            "SELECT * FROM refunds WHERE payment_id = ?", (payment_id,)
        ).fetchone()
        return _to_refund(row) if row else None

    def list_by_state(self, state: RefundState) -> list[Refund]:
        rows = self._conn.execute(
            "SELECT * FROM refunds WHERE state = ? ORDER BY created_at, id", (state.value,)
        ).fetchall()
        return [_to_refund(r) for r in rows]

    def list_filtered(
        self, requested_by: str | None, state: RefundState | None, limit: int
    ) -> list[Refund]:
        rows = self._conn.execute(
            "SELECT * FROM refunds WHERE (? IS NULL OR requested_by = ?)"
            " AND (? IS NULL OR state = ?) ORDER BY created_at DESC, id LIMIT ?",
            (requested_by, requested_by, state and state.value, state and state.value, limit),
        ).fetchall()
        return [_to_refund(r) for r in rows]

    def update_state(
        self,
        refund_id: str,
        state: RefundState,
        updated_at: str,
        decided_by: str | None = None,
        reason_code: str | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE refunds SET state = ?, decided_by = COALESCE(?, decided_by),"
            " reason_code = COALESCE(?, reason_code), updated_at = ? WHERE id = ?",
            (state.value, decided_by, reason_code, updated_at, refund_id),
        )
