from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.lib.timeutil import iso_z
from tests.support.fake_clock import FakeClock

OPS = {"X-Role": "ops"}
ADM = {"X-Role": "admin"}
CUST = {"X-Role": "customer", "X-Customer-Id": "cus_001"}


@pytest.fixture
def env(tmp_path: Path) -> Iterator[tuple[TestClient, FakeClock]]:
    clock = FakeClock()
    app = create_app(Settings(db_path=tmp_path / "t.db"), clock)
    with TestClient(app) as c:
        yield c, clock


def _submit(c: TestClient, pid: str, at: str) -> None:
    with c.app.state.container.db.write() as conn:  # type: ignore[attr-defined]
        conn.execute(
            "INSERT INTO payments (id, customer_id, idempotency_key, request_hash, amount_paise,"
            " rail, beneficiary, state, submitted_at, created_at, updated_at)"
            " VALUES (?, 'cus_001', ?, 'h', 100, 'UPI', 'B', 'SUBMITTED', ?, ?, ?)",
            (pid, pid, at, at, at),
        )


def _events(c: TestClient, pid: str) -> int:
    with c.app.state.container.db.read() as conn:  # type: ignore[attr-defined]
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM payment_events WHERE payment_id=?"
                " AND type='PAYMENT_FLAGGED_STUCK'",
                (pid,),
            ).fetchone()[0]
        )


def test_threshold_is_strict_and_age_reported(env: tuple[TestClient, FakeClock]) -> None:
    c, clock = env
    now = clock.now()
    from datetime import timedelta

    _submit(c, "pay_old", iso_z(now - timedelta(seconds=301)))
    _submit(c, "pay_edge", iso_z(now - timedelta(seconds=300)))
    _submit(c, "pay_new", iso_z(now - timedelta(seconds=299)))
    body = c.get("/ops/stuck-payments", headers=OPS).json()
    assert [i["payment_id"] for i in body["items"]] == ["pay_old"]
    assert body["total"] == 1 and body["items"][0]["age_seconds"] == 301
    assert c.get("/ops/stuck-payments", headers=ADM).status_code == 200


def test_customer_forbidden_and_unauthenticated(env: tuple[TestClient, FakeClock]) -> None:
    c, _ = env
    assert c.get("/ops/stuck-payments", headers=CUST).status_code == 403
    assert c.get("/ops/stuck-payments").status_code == 401


def test_no_duplicate_events_and_resolution_removes(env: tuple[TestClient, FakeClock]) -> None:
    c, clock = env
    from datetime import timedelta

    _submit(c, "pay_old", iso_z(clock.now() - timedelta(seconds=400)))
    for _ in range(3):
        c.get("/ops/stuck-payments", headers=OPS)
    assert _events(c, "pay_old") == 1
    with c.app.state.container.db.write() as conn:  # type: ignore[attr-defined]
        conn.execute(
            "UPDATE payments SET state='COMPLETED', rail_reference='r',"
            " completed_at='2026-10-04T09:30:00Z' WHERE id='pay_old'"
        )
    assert c.get("/ops/stuck-payments", headers=OPS).json()["items"] == []
    assert _events(c, "pay_old") == 1
