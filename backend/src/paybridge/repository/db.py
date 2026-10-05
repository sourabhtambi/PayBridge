"""Database access: connection factory with per-connection pragmas and transactions."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path: Path | str, busy_timeout_ms: int = 10000) -> None:
        self._path = str(path)
        self._busy_timeout_ms = busy_timeout_ms

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._path, isolation_level=None, timeout=self._busy_timeout_ms / 1000
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={int(self._busy_timeout_ms)}")
        return conn

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """Open a connection inside BEGIN IMMEDIATE; commit on success, roll back on error."""
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
        finally:
            conn.close()
