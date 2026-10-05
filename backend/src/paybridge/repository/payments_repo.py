"""Payments persistence: insert, lookup, listing and idempotency slot release."""

import sqlite3

from paybridge.lib.timeutil import iso_z, ist_day_bounds_utc
from paybridge.repository._sql import execute_unique
from paybridge.types.enums import PaymentState, Rail
from paybridge.types.models import Payment

_INSERT = """INSERT INTO payments (id, customer_id, idempotency_key, request_hash, amount_paise,
  rail, beneficiary, state, reason_code, rail_reference, submitted_at, completed_at,
  stuck_flagged_at, idempotency_released_at, created_at, updated_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""


def _to_payment(row: sqlite3.Row) -> Payment:
    return Payment(
        id=row["id"],
        customer_id=row["customer_id"],
        idempotency_key=row["idempotency_key"],
        request_hash=row["request_hash"],
        amount_paise=row["amount_paise"],
        rail=Rail(row["rail"]),
        beneficiary=row["beneficiary"],
        state=PaymentState(row["state"]),
        reason_code=row["reason_code"],
        rail_reference=row["rail_reference"],
        submitted_at=row["submitted_at"],
        completed_at=row["completed_at"],
        stuck_flagged_at=row["stuck_flagged_at"],
        idempotency_released_at=row["idempotency_released_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PaymentsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, p: Payment) -> None:
        execute_unique(
            self._conn,
            _INSERT,
            (
                p.id,
                p.customer_id,
                p.idempotency_key,
                p.request_hash,
                p.amount_paise,
                p.rail.value,
                p.beneficiary,
                p.state.value,
                p.reason_code,
                p.rail_reference,
                p.submitted_at,
                p.completed_at,
                p.stuck_flagged_at,
                p.idempotency_released_at,
                p.created_at,
                p.updated_at,
            ),
            "idempotency key for customer",
        )

    def get(self, payment_id: str) -> Payment | None:
        row = self._conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        return _to_payment(row) if row else None

    def distinct_beneficiaries(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT beneficiary FROM payments").fetchall()
        return [row["beneficiary"] for row in rows]

    def find_active_by_key(self, customer_id: str, idempotency_key: str) -> Payment | None:
        row = self._conn.execute(
            "SELECT * FROM payments WHERE customer_id = ? AND idempotency_key = ?"
            " AND idempotency_released_at IS NULL",
            (customer_id, idempotency_key),
        ).fetchone()
        return _to_payment(row) if row else None

    def release_idempotency(self, payment_id: str, now: str) -> bool:
        cur = self._conn.execute(
            "UPDATE payments SET idempotency_released_at = ?"
            " WHERE id = ? AND idempotency_released_at IS NULL",
            (now, payment_id),
        )
        return cur.rowcount == 1

    def list_recent(self, customer_id: str | None, limit: int) -> list[Payment]:
        if customer_id is None:
            rows = self._conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM payments WHERE customer_id = ?"
                " ORDER BY created_at DESC, id DESC LIMIT ?",
                (customer_id, limit),
            ).fetchall()
        return [_to_payment(r) for r in rows]

    def list_filtered(
        self, customer_id: str | None, state: PaymentState | None, limit: int
    ) -> list[Payment]:
        where, args = [], []
        if customer_id is not None:
            where.append("customer_id = ?")
            args.append(customer_id)
        if state is not None:
            where.append("state = ?")
            args.append(state.value)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        rows = self._conn.execute(
            f"SELECT * FROM payments{clause} ORDER BY created_at DESC, id DESC LIMIT ?",
            (*args, limit),
        ).fetchall()
        return [_to_payment(r) for r in rows]

    def list_completed_on_ist_day(self, business_day: str) -> list[Payment]:
        """COMPLETED payments with completed_at in [D 00:00 IST, D+1 00:00 IST)."""
        start, end = ist_day_bounds_utc(business_day)
        return self.list_completed_between(iso_z(start), iso_z(end))

    def list_completed_between(self, start: str, end: str) -> list[Payment]:
        """COMPLETED payments with start <= completed_at < end (ISO Z strings)."""
        rows = self._conn.execute(
            "SELECT * FROM payments WHERE state = 'COMPLETED' AND completed_at >= ?"
            " AND completed_at < ? ORDER BY completed_at, id",
            (start, end),
        ).fetchall()
        return [_to_payment(r) for r in rows]

    def mark_submitted(self, payment_id: str, now: str) -> None:
        self._conn.execute(
            "UPDATE payments SET state = 'SUBMITTED', submitted_at = ?, updated_at = ?"
            " WHERE id = ? AND state = 'CREATED'",
            (now, now, payment_id),
        )

    def mark_completed(self, payment_id: str, rail_reference: str, now: str) -> None:
        self._conn.execute(
            "UPDATE payments SET state = 'COMPLETED', rail_reference = ?, completed_at = ?,"
            " updated_at = ? WHERE id = ? AND state = 'SUBMITTED'",
            (rail_reference, now, now, payment_id),
        )

    def mark_refunded(self, payment_id: str, now: str) -> None:
        self._conn.execute(
            "UPDATE payments SET state = 'REFUNDED', updated_at = ?"
            " WHERE id = ? AND state = 'COMPLETED'",
            (now, payment_id),
        )

    def mark_failed(self, payment_id: str, reason_code: str, now: str) -> None:
        self._conn.execute(
            "UPDATE payments SET state = 'FAILED', reason_code = ?, updated_at = ?"
            " WHERE id = ? AND state IN ('CREATED','SUBMITTED')",
            (reason_code, now, payment_id),
        )

    def find_unflagged_submitted_before(self, cutoff: str) -> list[Payment]:
        rows = self._conn.execute(
            "SELECT * FROM payments WHERE state = 'SUBMITTED' AND stuck_flagged_at IS NULL"
            " AND submitted_at < ?",
            (cutoff,),
        ).fetchall()
        return [_to_payment(r) for r in rows]

    def mark_stuck_flagged(self, payment_id: str, now: str) -> bool:
        cur = self._conn.execute(
            "UPDATE payments SET stuck_flagged_at = ? WHERE id = ? AND state = 'SUBMITTED'"
            " AND stuck_flagged_at IS NULL",
            (now, payment_id),
        )
        return cur.rowcount == 1

    def list_flagged_submitted(self) -> list[Payment]:
        rows = self._conn.execute(
            "SELECT * FROM payments WHERE state = 'SUBMITTED' AND stuck_flagged_at IS NOT NULL"
            " ORDER BY submitted_at, id"
        ).fetchall()
        return [_to_payment(r) for r in rows]

    def rail_totals(self, start: str, end: str) -> dict[Rail, tuple[int, int]]:
        """Per-rail (count, total_paise) for payments created in [start, end)."""
        rows = self._conn.execute(
            "SELECT rail, COUNT(*) AS n, COALESCE(SUM(amount_paise), 0) AS total FROM payments"
            " WHERE created_at >= ? AND created_at < ? GROUP BY rail",
            (start, end),
        ).fetchall()
        return {Rail(r["rail"]): (r["n"], r["total"]) for r in rows}

    def state_counts(self, start: str, end: str) -> dict[PaymentState, int]:
        rows = self._conn.execute(
            "SELECT state, COUNT(*) AS n FROM payments"
            " WHERE created_at >= ? AND created_at < ? GROUP BY state",
            (start, end),
        ).fetchall()
        return {PaymentState(r["state"]): r["n"] for r in rows}
