import sqlite3
from pathlib import Path

import pytest

from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.migrate import initialize_database
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.types.enums import EventType, PaymentState
from paybridge.types.errors import DuplicateKeyError
from paybridge.types.models import PaymentEvent
from tests.support.factories import TS, make_payment, make_refund

TABLES = {
    "customers",
    "payments",
    "payment_attempts",
    "outbox_messages",
    "payment_events",
    "refunds",
    "rail_statement_entries",
    "reconciliation_results",
    "settlement_files",
}


def test_creates_nine_tables_and_wal(database: Database) -> None:
    with database.read() as c:
        names = {
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert names == TABLES
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert c.execute("PRAGMA synchronous").fetchone()[0] == 1
        assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert c.execute("PRAGMA busy_timeout").fetchone()[0] == 10000


def test_initialize_twice_preserves_rows(conn: sqlite3.Connection, database: Database) -> None:
    initialize_database(database)
    assert conn.execute("SELECT count(*) FROM customers").fetchone()[0] == 5


def test_no_real_columns(conn: sqlite3.Connection) -> None:
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        for col in conn.execute(f"PRAGMA table_info({table})"):
            assert col["type"].upper() not in {"REAL", "FLOAT", "DOUBLE"}
            if col["name"].endswith("_paise"):
                assert col["type"] == "INTEGER"


# AC-02
def test_duplicate_payment_key_and_partial_index(conn: sqlite3.Connection) -> None:
    repo = PaymentsRepo(conn)
    repo.insert(make_payment())
    with pytest.raises(DuplicateKeyError):
        repo.insert(make_payment(id="pay_000000000002"))
    repo.insert(make_payment(id="pay_000000000003", customer_id="cus_002"))
    assert repo.release_idempotency("pay_000000000001", TS)
    repo.insert(make_payment(id="pay_000000000004"))


def test_duplicate_refund(conn: sqlite3.Connection) -> None:
    PaymentsRepo(conn).insert(make_payment())
    refunds = RefundsRepo(conn)
    refunds.insert(make_refund())
    with pytest.raises(DuplicateKeyError):
        refunds.insert(make_refund(id="rfd_000000000002"))


# AC-09
def test_events_append_only(conn: sqlite3.Connection) -> None:
    PaymentsRepo(conn).insert(make_payment())
    repo = EventsRepo(conn)
    for i in range(3):
        repo.append(
            PaymentEvent(
                f"evt_00000000000{i}",
                "pay_000000000001",
                EventType.PAYMENT_CREATED,
                f'{{"n":{i}}}',
                TS,
            )
        )
    assert [e.payload for e in repo.list_for_payment("pay_000000000001")] == [
        '{"n":0}',
        '{"n":1}',
        '{"n":2}',
    ]
    public = [n for n in dir(EventsRepo) if not n.startswith("_")]
    assert sorted(public) == ["append", "list_for_payment"]
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE payment_events SET payload = '{}'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM payment_events")
    assert len(repo.list_for_payment("pay_000000000001")) == 3
    with pytest.raises(sqlite3.IntegrityError):
        repo.append(
            PaymentEvent("evt_bad", "pay_000000000001", EventType.PAYMENT_CREATED, "{x", TS)
        )


@pytest.mark.parametrize(("amount", "ok"), [(99, False), (100, True), (0, False), (-1, False)])
def test_payment_amount_check(conn: sqlite3.Connection, amount: int, ok: bool) -> None:
    repo = PaymentsRepo(conn)
    if ok:
        repo.insert(make_payment(amount_paise=amount))
    else:
        with pytest.raises(sqlite3.IntegrityError):
            repo.insert(make_payment(amount_paise=amount))


@pytest.mark.parametrize(("amount", "ok"), [(99, False), (100, True)])
def test_refund_amount_check(conn: sqlite3.Connection, amount: int, ok: bool) -> None:
    PaymentsRepo(conn).insert(make_payment())
    repo = RefundsRepo(conn)
    if ok:
        repo.insert(make_refund(amount_paise=amount))
    else:
        with pytest.raises(sqlite3.IntegrityError):
            repo.insert(make_refund(amount_paise=amount))


def test_statement_amount_zero_ok_negative_fails(conn: sqlite3.Connection) -> None:
    sql = (
        "INSERT INTO rail_statement_entries (id, rail, payment_ref, amount_paise,"
        " statement_date, created_at) VALUES (?, 'UPI', ?, ?, '2026-10-04', ?)"
    )
    conn.execute(sql, ("rse_1", "r1", 0, TS))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, ("rse_2", "r2", -1, TS))


# AC-04
def test_payment_state_checks(conn: sqlite3.Connection) -> None:
    repo = PaymentsRepo(conn)
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert(make_payment(state=PaymentState.COMPLETED))
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert(make_payment(state=PaymentState.FAILED))
    repo.insert(make_payment(state=PaymentState.FAILED, reason_code="LIMIT_EXCEEDED"))
    repo.insert(
        make_payment(
            id="pay_000000000002",
            idempotency_key="k2",
            state=PaymentState.COMPLETED,
            rail_reference="R1",
            completed_at=TS,
        )
    )


def test_foreign_keys_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        PaymentsRepo(conn).insert(make_payment(customer_id="nobody"))


# AC-07
def test_settlement_check_and_append_only(conn: sqlite3.Connection) -> None:
    from paybridge.repository.settlement_repo import SettlementRepo
    from paybridge.types.enums import SettlementKind
    from paybridge.types.models import SettlementFile

    repo = SettlementRepo(conn)
    f = SettlementFile("stl_1", "2026-10-04", SettlementKind.PRIMARY, 0, "a.csv", 1, "c", TS)
    repo.insert(f)
    assert repo.get("stl_1") == f
    assert repo.list_all() == [f]
    assert repo.get("nope") is None
    bad_seq = SettlementFile("stl_2", "2026-10-05", SettlementKind.PRIMARY, 1, "b", 1, "c", TS)
    with pytest.raises(sqlite3.IntegrityError):
        repo.insert(bad_seq)
    dup = SettlementFile("stl_3", "2026-10-04", SettlementKind.PRIMARY, 0, "c.csv", 1, "c", TS)
    with pytest.raises(DuplicateKeyError):
        repo.insert(dup)
    with pytest.raises(sqlite3.DatabaseError, match="settlement_files is append-only"):
        conn.execute("UPDATE settlement_files SET row_count = 2")
    with pytest.raises(sqlite3.DatabaseError, match="settlement_files is append-only"):
        conn.execute("DELETE FROM settlement_files")


def test_write_transaction_rolls_back(database: Database) -> None:
    with pytest.raises(RuntimeError), database.write() as c:
        c.execute("INSERT INTO customers VALUES ('x','X','customer','t')")
        raise RuntimeError("boom")
    with database.read() as c:
        assert c.execute("SELECT count(*) FROM customers").fetchone()[0] == 0
    with database.write() as c:
        c.execute("INSERT INTO customers VALUES ('x','X','customer','t')")
    with database.read() as c:
        assert c.execute("SELECT count(*) FROM customers").fetchone()[0] == 1


def test_wal_failure_raises(tmp_path: Path) -> None:
    db = Database(":memory:")
    with pytest.raises(RuntimeError, match="WAL"):
        initialize_database(db)
