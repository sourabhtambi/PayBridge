"""Outbox message persistence."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import OutboxStatus
from paybridge.types.models import OutboxMessage


def _to_message(row: sqlite3.Row) -> OutboxMessage:
    return OutboxMessage(
        id=row["id"],
        payment_id=row["payment_id"],
        status=OutboxStatus(row["status"]),
        next_attempt_at=row["next_attempt_at"],
        attempts=row["attempts"],
        claimed_at=row["claimed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class OutboxRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, payment_id: str, next_attempt_at: str, now: str) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO outbox_messages (payment_id, status, next_attempt_at, attempts,"
            " created_at, updated_at) VALUES (?, 'PENDING', ?, 0, ?, ?)",
            (payment_id, next_attempt_at, now, now),
            "outbox message for payment",
        )

    def get_for_payment(self, payment_id: str) -> OutboxMessage | None:
        row = self._conn.execute(
            "SELECT * FROM outbox_messages WHERE payment_id = ?", (payment_id,)
        ).fetchone()
        return _to_message(row) if row else None

    def list_due(self, now: str, limit: int) -> list[OutboxMessage]:
        rows = self._conn.execute(
            "SELECT * FROM outbox_messages WHERE status IN ('PENDING', 'IN_PROGRESS')"
            " AND next_attempt_at <= ?"
            " ORDER BY next_attempt_at, id LIMIT ?",
            (now, limit),
        ).fetchall()
        return [_to_message(r) for r in rows]

    def mark_in_progress(self, message_id: int, now: str) -> None:
        self._conn.execute(
            "UPDATE outbox_messages SET status = 'IN_PROGRESS', claimed_at = ?, updated_at = ?"
            " WHERE id = ?",
            (now, now, message_id),
        )

    def mark_sent(self, message_id: int, attempts: int, now: str) -> None:
        self._conn.execute(
            "UPDATE outbox_messages SET status = 'SENT', attempts = ?, updated_at = ? WHERE id = ?",
            (attempts, now, message_id),
        )

    def reschedule(self, message_id: int, attempts: int, next_attempt_at: str, now: str) -> None:
        self._conn.execute(
            "UPDATE outbox_messages SET status = 'PENDING', attempts = ?, next_attempt_at = ?,"
            " updated_at = ? WHERE id = ?",
            (attempts, next_attempt_at, now, message_id),
        )
