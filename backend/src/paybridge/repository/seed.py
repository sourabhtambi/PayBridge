"""Idempotent demo users for all three roles."""

import sqlite3

from paybridge.lib.timeutil import iso_z
from paybridge.types.ports import Clock

DEMO_USERS: tuple[tuple[str, str, str], ...] = (
    ("cus_001", "Asha Verma", "customer"),
    ("cus_002", "Rohan Mehta", "customer"),
    ("cus_003", "Priya Nair", "customer"),
    ("ops_001", "Ops Analyst", "ops"),
    ("adm_001", "Admin", "admin"),
)


def seed_customers(conn: sqlite3.Connection, clock: Clock) -> None:
    created_at = iso_z(clock.now())
    conn.executemany(
        "INSERT OR IGNORE INTO customers (id, name, role, created_at) VALUES (?, ?, ?, ?)",
        [(uid, name, role, created_at) for uid, name, role in DEMO_USERS],
    )
