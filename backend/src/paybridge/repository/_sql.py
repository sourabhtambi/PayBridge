"""Shared repository helpers: uniqueness translation."""

import sqlite3
from collections.abc import Sequence

from paybridge.types.errors import DuplicateKeyError

SqlParam = str | int | None


def execute_unique(
    conn: sqlite3.Connection, sql: str, params: Sequence[SqlParam], what: str
) -> sqlite3.Cursor:
    """Run an INSERT, translating UNIQUE violations into DuplicateKeyError."""
    try:
        return conn.execute(sql, params)
    except sqlite3.IntegrityError as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise DuplicateKeyError(f"Duplicate {what}") from exc
        raise
