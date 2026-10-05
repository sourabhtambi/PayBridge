"""Append-only payment events: only append and list_for_payment are exposed."""

import sqlite3

from paybridge.repository._sql import execute_unique
from paybridge.types.enums import EventType
from paybridge.types.models import PaymentEvent


class EventsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def append(self, event: PaymentEvent) -> None:
        execute_unique(
            self._conn,
            "INSERT INTO payment_events (id, payment_id, type, payload, at) VALUES (?, ?, ?, ?, ?)",
            (event.id, event.payment_id, event.type.value, event.payload, event.at),
            "event id",
        )

    def list_for_payment(self, payment_id: str) -> list[PaymentEvent]:
        rows = self._conn.execute(
            "SELECT * FROM payment_events WHERE payment_id = ? ORDER BY rowid", (payment_id,)
        ).fetchall()
        return [
            PaymentEvent(
                id=r["id"],
                payment_id=r["payment_id"],
                type=EventType(r["type"]),
                payload=r["payload"],
                at=r["at"],
            )
            for r in rows
        ]
