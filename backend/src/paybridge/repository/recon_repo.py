"""Reconciliation results persistence."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import Rail, ReconStatus
from paybridge.types.models import ReconciliationResult


def _to_result(r: sqlite3.Row) -> ReconciliationResult:
    return ReconciliationResult(
        id=r["id"],
        statement_date=r["statement_date"],
        rail=Rail(r["rail"]),
        status=ReconStatus(r["status"]),
        payment_id=r["payment_id"],
        statement_entry_id=r["statement_entry_id"],
        payment_ref=r["payment_ref"],
        payment_amount_paise=r["payment_amount_paise"],
        statement_amount_paise=r["statement_amount_paise"],
        resolved=bool(r["resolved"]),
        resolution_note=r["resolution_note"],
        resolved_by=r["resolved_by"],
        resolved_at=r["resolved_at"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


class ReconRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, x: ReconciliationResult) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO reconciliation_results (id, statement_date, rail, status, payment_id,"
            " statement_entry_id, payment_ref, payment_amount_paise, statement_amount_paise,"
            " resolved, resolution_note, resolved_by, resolved_at, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                x.id,
                x.statement_date,
                x.rail.value,
                x.status.value,
                x.payment_id,
                x.statement_entry_id,
                x.payment_ref,
                x.payment_amount_paise,
                x.statement_amount_paise,
                int(x.resolved),
                x.resolution_note,
                x.resolved_by,
                x.resolved_at,
                x.created_at,
                x.updated_at,
            ),
            "reconciliation result",
        )

    def get(self, result_id: str) -> ReconciliationResult | None:
        row = self._conn.execute(
            "SELECT * FROM reconciliation_results WHERE id = ?", (result_id,)
        ).fetchone()
        return _to_result(row) if row else None

    def list_unresolved(self) -> list[ReconciliationResult]:
        rows = self._conn.execute(
            "SELECT * FROM reconciliation_results WHERE resolved = 0 AND status <> 'matched'"
            " ORDER BY statement_date, id"
        ).fetchall()
        return [_to_result(r) for r in rows]

    def list_by_date(self, statement_date: str) -> list[ReconciliationResult]:
        rows = self._conn.execute(
            "SELECT * FROM reconciliation_results WHERE statement_date = ? ORDER BY id",
            (statement_date,),
        ).fetchall()
        return [_to_result(r) for r in rows]

    def resolve(self, result_id: str, note: str, by: str, now: str) -> bool:
        cur = self._conn.execute(
            "UPDATE reconciliation_results SET resolved = 1, resolution_note = ?,"
            " resolved_by = ?, resolved_at = ?, updated_at = ? WHERE id = ? AND resolved = 0",
            (note, by, now, now, result_id),
        )
        return cur.rowcount == 1

    def status_for_payment(self, payment_id: str) -> ReconStatus | None:
        row = self._conn.execute(
            "SELECT status FROM reconciliation_results WHERE payment_id = ?"
            " ORDER BY created_at DESC, id DESC LIMIT 1",
            (payment_id,),
        ).fetchone()
        return ReconStatus(row["status"]) if row else None
