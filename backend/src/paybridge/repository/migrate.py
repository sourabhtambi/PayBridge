"""Database initialisation (idempotent) with WAL verification."""

from paybridge.repository.db import Database
from paybridge.repository.schema import STATEMENTS


def initialize_database(db: Database) -> None:
    conn = db.connect()
    try:
        mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        if mode != "wal":
            raise RuntimeError(f"SQLite WAL mode unavailable (journal_mode={mode})")
        conn.execute("BEGIN IMMEDIATE")
        try:
            for statement in STATEMENTS:
                conn.execute(statement)
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    finally:
        conn.close()
