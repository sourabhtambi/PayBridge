import sqlite3

import pytest

from paybridge.repository.customers_repo import CustomersRepo
from paybridge.repository.seed import seed_customers
from paybridge.types.enums import Role
from tests.support.fake_clock import FakeClock


def test_seed_idempotent(conn: sqlite3.Connection, clock: FakeClock) -> None:
    before = conn.execute("SELECT id, created_at FROM customers ORDER BY id").fetchall()
    clock.advance(3600)
    seed_customers(conn, clock)
    after = conn.execute("SELECT id, created_at FROM customers ORDER BY id").fetchall()
    assert [tuple(r) for r in before] == [tuple(r) for r in after]
    repo = CustomersRepo(conn)
    customers = repo.list_all()
    assert [c.id for c in customers] == ["adm_001", "cus_001", "cus_002", "cus_003", "ops_001"]
    roles = [c.role for c in customers]
    assert roles.count(Role.CUSTOMER) == 3
    assert roles.count(Role.OPS) == 1
    assert roles.count(Role.ADMIN) == 1
    assert all(c.name for c in customers)
    assert repo.get("cus_001") is not None
    assert repo.get("zzz") is None


def test_invalid_role_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO customers VALUES ('z', 'Z', 'root', 't')")
