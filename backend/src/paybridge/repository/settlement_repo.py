"""Settlement file records: insert, get and list only (append-only table)."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import SettlementKind
from paybridge.types.models import SettlementFile


def _to_file(r: sqlite3.Row) -> SettlementFile:
    return SettlementFile(
        id=r["id"],
        business_date=r["business_date"],
        kind=SettlementKind(r["kind"]),
        sequence=r["sequence"],
        path=r["path"],
        row_count=r["row_count"],
        checksum=r["checksum"],
        written_at=r["written_at"],
    )


class SettlementRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, f: SettlementFile) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO settlement_files (id, business_date, kind, sequence, path, row_count,"
            " checksum, written_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f.id,
                f.business_date,
                f.kind.value,
                f.sequence,
                f.path,
                f.row_count,
                f.checksum,
                f.written_at,
            ),
            "settlement file",
        )

    def get(self, file_id: str) -> SettlementFile | None:
        row = self._conn.execute(
            "SELECT * FROM settlement_files WHERE id = ?", (file_id,)
        ).fetchone()
        return _to_file(row) if row else None

    def list_all(self) -> list[SettlementFile]:
        rows = self._conn.execute(
            "SELECT * FROM settlement_files ORDER BY business_date DESC, sequence DESC"
        ).fetchall()
        return [_to_file(r) for r in rows]

    def list_by_date(self, business_date: str) -> list[SettlementFile]:
        rows = self._conn.execute(
            "SELECT * FROM settlement_files WHERE business_date = ? ORDER BY sequence",
            (business_date,),
        ).fetchall()
        return [_to_file(r) for r in rows]
