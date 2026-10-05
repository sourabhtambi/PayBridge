"""Test-only: empty every table except customers (append-only triggers dropped first)."""

from paybridge.repository.db import Database


def wipe_database(db: Database) -> None:
    with db.write() as conn:
        conn.execute("PRAGMA defer_foreign_keys = ON")
        for (name,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall():
            conn.execute(f'DROP TRIGGER "{name}"')
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
            " AND name NOT LIKE 'sqlite_%' AND name != 'customers'"
        ).fetchall()
        for (name,) in tables:
            conn.execute(f'DELETE FROM "{name}"')
