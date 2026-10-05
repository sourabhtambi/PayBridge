"""Rail statement entries."""

import sqlite3

from paybridge.types.enums import Rail, ReconStatus
from paybridge.types.models import RailStatementEntry


class StatementsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert_or_ignore(self, e: RailStatementEntry) -> bool:
        """Insert an entry; return False when (rail, payment_ref, statement_date) exists."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO rail_statement_entries (id, rail, payment_ref, payment_id,"
            " amount_paise, status, statement_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                e.id,
                e.rail.value,
                e.payment_ref,
                e.payment_id,
                e.amount_paise,
                e.status.value if e.status else None,
                e.statement_date,
                e.created_at,
            ),
        )
        return cur.rowcount == 1

    def list_by_date(self, statement_date: str) -> list[RailStatementEntry]:
        rows = self._conn.execute(
            "SELECT * FROM rail_statement_entries WHERE statement_date = ?"
            " ORDER BY rail, payment_ref",
            (statement_date,),
        ).fetchall()
        return [
            RailStatementEntry(
                id=r["id"],
                rail=Rail(r["rail"]),
                payment_ref=r["payment_ref"],
                payment_id=r["payment_id"],
                amount_paise=r["amount_paise"],
                status=ReconStatus(r["status"]) if r["status"] else None,
                statement_date=r["statement_date"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
