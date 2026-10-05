import sqlite3
from dataclasses import replace

from paybridge.repository.attempts_repo import AttemptsRepo
from paybridge.repository.outbox_repo import OutboxRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.types.enums import AttemptOutcome, OutboxStatus, Rail, ReconStatus
from paybridge.types.errors import DuplicateKeyError
from paybridge.types.models import RailStatementEntry, ReconciliationResult
from tests.support.factories import TS, make_payment


def test_get_find_list_release(conn: sqlite3.Connection) -> None:
    repo = PaymentsRepo(conn)
    p = make_payment()
    repo.insert(p)
    repo.insert(
        make_payment(id="pay_000000000002", idempotency_key="k2", created_at="2026-10-04T10:00:00Z")
    )
    repo.insert(make_payment(id="pay_000000000003", idempotency_key="k3", customer_id="cus_002"))
    assert repo.get(p.id) == p
    assert repo.get("none") is None
    assert repo.find_active_by_key("cus_001", "key-1") == p
    assert repo.find_active_by_key("cus_001", "zzz") is None
    assert [x.id for x in repo.list_recent("cus_001", 10)] == ["pay_000000000002", p.id]
    assert len(repo.list_recent(None, 10)) == 3
    assert repo.release_idempotency(p.id, TS)
    assert not repo.release_idempotency(p.id, TS)
    assert repo.find_active_by_key("cus_001", "key-1") is None
    assert repo.get(p.id) == replace(p, idempotency_released_at=TS)


def test_attempts_and_outbox(conn: sqlite3.Connection) -> None:
    PaymentsRepo(conn).insert(make_payment())
    attempts = AttemptsRepo(conn)
    attempts.insert("pay_000000000001", 1, AttemptOutcome.TRANSIENT, TS)
    attempts.insert("pay_000000000001", 2, AttemptOutcome.PERMANENT, TS, "LIMIT_EXCEEDED")
    got = attempts.list_for_payment("pay_000000000001")
    assert [a.attempt_no for a in got] == [1, 2]
    assert got[1].error_code == "LIMIT_EXCEEDED"
    try:
        attempts.insert("pay_000000000001", 1, AttemptOutcome.SUCCESS, TS)
        raise AssertionError("expected duplicate")
    except DuplicateKeyError:
        pass
    outbox = OutboxRepo(conn)
    outbox.insert("pay_000000000001", TS, TS)
    msg = outbox.get_for_payment("pay_000000000001")
    assert msg is not None
    assert msg.status is OutboxStatus.PENDING
    assert outbox.get_for_payment("x") is None
    assert outbox.list_due("2026-10-04T09:29:59Z", 10) == []
    assert outbox.list_due(TS, 10) == [msg]
    try:
        outbox.insert("pay_000000000001", TS, TS)
        raise AssertionError("expected duplicate")
    except DuplicateKeyError:
        pass


def test_statements_and_recon(conn: sqlite3.Connection) -> None:
    PaymentsRepo(conn).insert(make_payment())
    stmts = StatementsRepo(conn)
    e = RailStatementEntry(
        "rse_1", Rail.UPI, "ref", 5, "2026-10-04", TS, status=ReconStatus.MATCHED
    )
    assert stmts.insert_or_ignore(e)
    assert not stmts.insert_or_ignore(replace(e, id="rse_2"))
    assert stmts.insert_or_ignore(replace(e, id="rse_3", payment_ref="r2", status=None))
    assert [x.id for x in stmts.list_by_date("2026-10-04")] == ["rse_3", "rse_1"]
    assert stmts.list_by_date("2026-10-05") == []

    recon = ReconRepo(conn)
    r = ReconciliationResult(
        "rec_1",
        "2026-10-04",
        Rail.UPI,
        ReconStatus.UNMATCHED_INTERNAL,
        TS,
        TS,
        payment_id="pay_000000000001",
    )
    recon.insert(r)
    try:
        recon.insert(replace(r, id="rec_2"))
        raise AssertionError("expected duplicate")
    except DuplicateKeyError:
        pass
    assert recon.get("rec_1") == r
    assert recon.get("none") is None
    assert recon.list_unresolved() == [r]
    assert recon.resolve("rec_1", "note", "ops_001", TS)
    assert not recon.resolve("rec_1", "again", "ops_001", TS)
    assert recon.list_unresolved() == []
    got = recon.get("rec_1")
    assert got is not None
    assert got.resolved
    assert got.resolution_note == "note"
