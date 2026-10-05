import asyncio
import sqlite3
import warnings
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.lib.timeutil import iso_z
from paybridge.repository.attempts_repo import AttemptsRepo
from paybridge.repository.db import Database
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.outbox_repo import OutboxRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.service.outbox_worker import OutboxWorker
from paybridge.service.payment_service import PaymentService
from paybridge.service.rail_adapters import build_adapters
from paybridge.types.enums import (
    AttemptOutcome,
    EventType,
    OutboxStatus,
    PaymentState,
    Rail,
    ReasonCode,
)
from paybridge.types.errors import PermanentRailError, TransientRailError
from paybridge.types.models import RailLedgerEntry
from tests.support.fake_clock import FakeClock


def test_worker_completes_payment(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    p = PaymentService(database, clock).create_payment("cus_001", "k", 150000, "Ravi").payment
    worker = OutboxWorker(database, clock, build_adapters(clock))
    assert asyncio.run(worker.process_once()) == 1
    stored = PaymentsRepo(conn).get(p.id)
    assert stored is not None and stored.state is PaymentState.COMPLETED
    assert stored.rail_reference
    attempts = AttemptsRepo(conn).list_for_payment(p.id)
    assert [a.outcome for a in attempts] == [AttemptOutcome.SUCCESS]
    types = [e.type for e in EventsRepo(conn).list_for_payment(p.id)]
    assert types[-2:] == [EventType.PAYMENT_SUBMITTED, EventType.PAYMENT_COMPLETED]
    msg = OutboxRepo(conn).get_for_payment(p.id)
    assert msg is not None and msg.status is OutboxStatus.SENT
    assert asyncio.run(worker.process_once()) == 0


def test_adapters_idempotent(clock: FakeClock) -> None:
    adapters = build_adapters(clock)
    assert set(adapters) == set(Rail)
    for adapter in adapters.values():
        a = asyncio.run(adapter.submit("pay_1", 100))
        assert asyncio.run(adapter.submit("pay_1", 100)).rail_ref == a.rail_ref
        r = asyncio.run(adapter.reverse("pay_1", 100))
        assert r.rail_ref != a.rail_ref


def test_lifespan_starts_and_stops_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYBRIDGE_DATA_DIR", str(tmp_path))
    settings = Settings.from_env()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with TestClient(create_app(settings)) as client:
            assert client.get("/health").status_code in (200, 404)


class _Flaky:
    """Adapter raising a scripted sequence of errors, then succeeding."""

    def __init__(self, errors: list[Exception], inner: object) -> None:
        self._errors = errors
        self._inner = inner

    async def submit(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        if self._errors:
            raise self._errors.pop(0)
        return await self._inner.submit(payment_id, amount_paise)  # type: ignore[attr-defined, no-any-return]

    async def reverse(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        raise NotImplementedError


def _setup(
    database: Database, clock: FakeClock, errors: list[Exception]
) -> tuple[OutboxWorker, str]:
    p = PaymentService(database, clock).create_payment("cus_001", "k", 150000, "Ravi").payment
    inner = build_adapters(clock)[p.rail]
    adapters = {r: _Flaky(errors, inner) for r in Rail}
    return OutboxWorker(database, clock, adapters), p.id  # type: ignore[arg-type]


# AC-05
def test_retry_then_success_with_backoff(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    worker, pid = _setup(database, clock, [TransientRailError("x"), TransientRailError("x")])
    asyncio.run(worker.process_once())
    msg = OutboxRepo(conn).get_for_payment(pid)
    assert msg is not None and msg.status is OutboxStatus.PENDING
    assert msg.next_attempt_at == iso_z(clock.now() + timedelta(seconds=1))
    assert asyncio.run(worker.process_once()) == 0
    clock.advance(1)
    asyncio.run(worker.process_once())
    msg = OutboxRepo(conn).get_for_payment(pid)
    assert msg is not None and msg.next_attempt_at == iso_z(clock.now() + timedelta(seconds=2))
    clock.advance(2)
    asyncio.run(worker.process_once())
    attempts = AttemptsRepo(conn).list_for_payment(pid)
    assert [a.outcome for a in attempts] == [
        AttemptOutcome.TRANSIENT,
        AttemptOutcome.TRANSIENT,
        AttemptOutcome.SUCCESS,
    ]
    stored = PaymentsRepo(conn).get(pid)
    assert stored is not None and stored.state is PaymentState.COMPLETED
    types = [e.type for e in EventsRepo(conn).list_for_payment(pid)]
    assert types.count(EventType.PAYMENT_RETRY_SCHEDULED) == 2
    assert types.count(EventType.PAYMENT_SUBMITTED) == 1


# AC-05
def test_retries_exhausted(database: Database, conn: sqlite3.Connection, clock: FakeClock) -> None:
    worker, pid = _setup(database, clock, [TransientRailError("x") for _ in range(5)])
    for delay in (1, 2, 4, 8):
        asyncio.run(worker.process_once())
        msg = OutboxRepo(conn).get_for_payment(pid)
        assert msg is not None and msg.next_attempt_at == iso_z(
            clock.now() + timedelta(seconds=delay)
        )
        clock.advance(delay)
    asyncio.run(worker.process_once())
    stored = PaymentsRepo(conn).get(pid)
    assert stored is not None and stored.state is PaymentState.FAILED
    assert stored.reason_code == "RETRIES_EXHAUSTED"
    assert len(AttemptsRepo(conn).list_for_payment(pid)) == 5
    types = [e.type for e in EventsRepo(conn).list_for_payment(pid)]
    assert types.count(EventType.PAYMENT_RETRY_SCHEDULED) == 4
    assert types[-1] is EventType.PAYMENT_FAILED
    assert asyncio.run(worker.process_once()) == 0


# AC-05
def test_permanent_failure_immediate(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    worker, pid = _setup(
        database, clock, [PermanentRailError("no", ReasonCode.INSUFFICIENT_FUNDS.value)]
    )
    asyncio.run(worker.process_once())
    stored = PaymentsRepo(conn).get(pid)
    assert stored is not None and stored.state is PaymentState.FAILED
    assert stored.reason_code == "INSUFFICIENT_FUNDS"
    attempts = AttemptsRepo(conn).list_for_payment(pid)
    assert [a.outcome for a in attempts] == [AttemptOutcome.PERMANENT]
    types = [e.type for e in EventsRepo(conn).list_for_payment(pid)]
    assert types[-1] is EventType.PAYMENT_FAILED


class _CrashAfterAccept:
    """Rail accepts the payment, then the process 'dies' before the DB update."""

    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.armed = True

    async def submit(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        entry: RailLedgerEntry = await self._inner.submit(payment_id, amount_paise)  # type: ignore[attr-defined]
        if self.armed:
            raise KeyboardInterrupt
        return entry

    async def reverse(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        return await self._inner.reverse(payment_id, amount_paise)  # type: ignore[attr-defined, no-any-return]


def test_crash_batch_resumes_exactly_once(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    svc = PaymentService(database, clock)
    ids = [svc.create_payment("cus_001", f"k{i}", 1000, "R").payment.id for i in range(10)]
    adapters = build_adapters(clock)
    crashing = {r: _CrashAfterAccept(a) for r, a in adapters.items()}
    try:
        asyncio.run(OutboxWorker(database, clock, crashing).process_once())  # type: ignore[arg-type]
    except KeyboardInterrupt:
        pass
    msg = OutboxRepo(conn).get_for_payment(ids[0])
    assert msg is not None and msg.status is OutboxStatus.IN_PROGRESS
    asyncio.run(OutboxWorker(database, clock, adapters).process_once())
    asyncio.run(OutboxWorker(database, clock, adapters).process_once())
    for pid in ids:
        stored = PaymentsRepo(conn).get(pid)
        assert stored is not None and stored.state is PaymentState.COMPLETED
        events = EventsRepo(conn).list_for_payment(pid)
        assert [e.type for e in events].count(EventType.PAYMENT_COMPLETED) == 1
    first = PaymentsRepo(conn).get(ids[0])
    again = asyncio.run(adapters[first.rail].submit(ids[0], 1000))  # type: ignore[union-attr]
    assert again.rail_ref == first.rail_reference  # type: ignore[union-attr]


def test_worker_skips_rows_before_next_attempt_at(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    p = PaymentService(database, clock).create_payment("cus_001", "k", 1000, "R").payment
    with database.write() as c:
        c.execute(
            "UPDATE outbox_messages SET next_attempt_at = ? WHERE payment_id = ?",
            (iso_z(clock.now() + timedelta(seconds=60)), p.id),
        )
    worker = OutboxWorker(database, clock, build_adapters(clock))
    assert asyncio.run(worker.process_once()) == 0
    clock.advance(61)
    assert asyncio.run(worker.process_once()) == 1


class _FlakyAdapter:
    """Raises an unexpected (non-rail) error on the first submit, then succeeds."""

    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.calls = 0

    async def submit(self, payment_id: str, amount_paise: int) -> RailLedgerEntry:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("unexpected adapter bug")
        return await self._inner.submit(payment_id, amount_paise)  # type: ignore[attr-defined,no-any-return]


def test_run_survives_unexpected_errors_and_keeps_processing(
    database: Database, conn: sqlite3.Connection, clock: FakeClock
) -> None:
    """A single unexpected exception must not kill the worker loop (stuck CREATED payments)."""
    p = PaymentService(database, clock).create_payment("cus_001", "k", 15_000_000, "Ravi").payment
    adapters = build_adapters(clock)
    flaky = _FlakyAdapter(adapters[Rail.IMPS])
    adapters[Rail.IMPS] = flaky  # type: ignore[assignment]
    worker = OutboxWorker(database, clock, adapters, poll_interval=0.01)

    async def run_briefly() -> None:
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.3)
        assert not task.done(), "worker loop died"
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(run_briefly())
    stored = PaymentsRepo(conn).get(p.id)
    assert stored is not None and stored.state is PaymentState.COMPLETED
    assert flaky.calls == 2
