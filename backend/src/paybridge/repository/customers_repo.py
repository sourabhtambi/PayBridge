"""Customers read access."""

import sqlite3

from paybridge.types.enums import Role
from paybridge.types.models import Customer


def _to_customer(row: sqlite3.Row) -> Customer:
    return Customer(
        id=row["id"], name=row["name"], role=Role(row["role"]), created_at=row["created_at"]
    )


class CustomersRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, customer_id: str) -> Customer | None:
        row = self._conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return _to_customer(row) if row else None

    def list_all(self) -> list[Customer]:
        rows = self._conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
        return [_to_customer(r) for r in rows]
