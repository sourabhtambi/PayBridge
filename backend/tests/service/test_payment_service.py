import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.outbox_repo import OutboxRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.service.payment_service import PaymentService
from paybridge.types.enums import EventType, OutboxStatus, PaymentState, Rail
from paybridge.types.errors import IdempotencyConflict, ValidationError
from tests.support.fake_clock import FakeClock


@pytest.fixture
def svc(database: Database, conn: sqlite3.Connection, clock: FakeClock) -> PaymentService:
    return PaymentService(database, clock)


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


# AC-01, AC-09
def test_create_persists_payment_outbox_event(
    svc: PaymentService, conn: sqlite3.Connection
) -> None:
    p = svc.create_payment("cus_001", "k1", 150000, "Ravi").payment
    stored = PaymentsRepo(conn).get(p.id)
    assert stored is not None and stored.rail is Rail.UPI and stored.state is PaymentState.CREATED
    msg = OutboxRepo(conn).get_for_payment(p.id)
    assert msg is not None and msg.status is OutboxStatus.PENDING
    events = EventsRepo(conn).list_for_payment(p.id)
    assert [e.type for e in events] == [EventType.PAYMENT_CREATED]


def test_outbox_failure_rolls_back(
    svc: PaymentService, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("outbox down")

    monkeypatch.setattr(OutboxRepo, "insert", boom)
    with pytest.raises(RuntimeError):
        svc.create_payment("cus_001", "k1", 150000, "Ravi")
    assert _count(conn, "payments") == 0
    assert _count(conn, "payment_events") == 0


# AC-03
def test_routing_reason_logged_in_created_event(
    svc: PaymentService, conn: sqlite3.Connection
) -> None:
    p = svc.create_payment("cus_001", "k-reason", 20_000_001, "Ravi").payment
    (event,) = EventsRepo(conn).list_for_payment(p.id)
    payload = json.loads(event.payload)
    assert payload["rail"] == "NEFT"
    assert payload["reason"] == "amount 20000001 paise > 20000000 and <= 50000000: NEFT"


@pytest.mark.parametrize(
    ("amount", "rail"),
    [(10_000_001, Rail.IMPS), (50_000_001, Rail.RTGS)],
)
# AC-03
def test_routing(svc: PaymentService, amount: int, rail: Rail) -> None:
    assert svc.create_payment("cus_001", "k", amount, "Ravi").payment.rail is rail


@pytest.mark.parametrize(("amount", "beneficiary"), [(99, "Ravi"), (10000, ""), (10000, "x" * 141)])
def test_validation_persists_nothing(
    svc: PaymentService, conn: sqlite3.Connection, amount: int, beneficiary: str
) -> None:
    with pytest.raises(ValidationError):
        svc.create_payment("cus_001", "k", amount, beneficiary)
    assert _count(conn, "payments") == 0
    assert _count(conn, "outbox_messages") == 0
    assert _count(conn, "payment_events") == 0


# AC-02
def test_replay_same_payload(svc: PaymentService, conn: sqlite3.Connection) -> None:
    a = svc.create_payment("cus_001", "k", 10000, "Ravi")
    b = svc.create_payment("cus_001", "k", 10000, "Ravi")
    assert not a.replay and b.replay and b.payment.id == a.payment.id
    assert _count(conn, "payments") == 1


# AC-02
@pytest.mark.parametrize(("amount", "ben"), [(20000, "Ravi"), (10000, "Other")])
def test_conflict_on_different_payload(
    svc: PaymentService, conn: sqlite3.Connection, amount: int, ben: str
) -> None:
    svc.create_payment("cus_001", "k", 10000, "Ravi")
    with pytest.raises(IdempotencyConflict):
        svc.create_payment("cus_001", "k", amount, ben)
    assert _count(conn, "payments") == 1


# AC-02
def test_concurrent_same_key(svc: PaymentService, conn: sqlite3.Connection) -> None:
    with ThreadPoolExecutor(20) as ex:
        results = list(
            ex.map(lambda _: svc.create_payment("cus_001", "k", 10000, "Ravi"), range(20))
        )
    assert sum(not r.replay for r in results) == 1
    assert sum(r.replay for r in results) == 19
    assert _count(conn, "payments") == 1


def test_same_key_different_customers(svc: PaymentService, conn: sqlite3.Connection) -> None:
    a = svc.create_payment("cus_001", "k", 10000, "Ravi")
    b = svc.create_payment("cus_002", "k", 10000, "Ravi")
    assert a.payment.id != b.payment.id and not b.replay
    assert _count(conn, "payments") == 2


def test_expired_key_creates_new(
    svc: PaymentService, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    a = svc.create_payment("cus_001", "k", 10000, "Ravi")
    clock.advance(86400)
    b = svc.create_payment("cus_001", "k", 20000, "Other")
    assert not b.replay and b.payment.id != a.payment.id
    orig = PaymentsRepo(conn).get(a.payment.id)
    assert orig is not None and orig.idempotency_released_at is not None
    assert orig.amount_paise == 10000 and orig.state is PaymentState.CREATED
    assert _count(conn, "payments") == 2
