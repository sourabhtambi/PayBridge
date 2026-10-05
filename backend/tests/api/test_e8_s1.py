# ruff: noqa: F811
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.repository.db import Database
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.types.enums import PaymentState, Rail
from tests.api.test_e5_s1 import ADMIN, C1, OPS, db_path  # noqa: F401
from tests.support.factories import make_payment, make_refund
from tests.support.fake_clock import FakeClock


@pytest.fixture
def client(db_path: Path, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(db_path=db_path, settlement_dir=tmp_path / "settlement")
    with TestClient(create_app(settings, FakeClock())) as c:
        yield c


def _ins(db_path: Path, pid: str, created: str, **kw: object) -> None:
    with Database(db_path).write() as conn:
        PaymentsRepo(conn).insert(
            make_payment(id=pid, idempotency_key=pid, created_at=created, updated_at=created, **kw)
        )


# AC-10
def test_aggregates_ist_boundaries(client: TestClient, db_path: Path) -> None:
    # IST 2026-10-04 = [2026-10-03T18:30Z, 2026-10-04T18:30Z)
    _ins(db_path, "p_before", "2026-10-03T18:29:59Z")
    _ins(db_path, "p_first", "2026-10-03T18:30:00Z", rail=Rail.UPI, amount_paise=100)
    _ins(
        db_path,
        "p_second",
        "2026-10-04T18:29:59Z",
        rail=Rail.UPI,
        amount_paise=250,
        state=PaymentState.FAILED,
        reason_code="LIMIT_EXCEEDED",
    )
    _ins(db_path, "p_after", "2026-10-04T18:30:00Z")
    with Database(db_path).write() as conn:
        RefundsRepo(conn).insert(make_refund(payment_id="p_first"))
    b = client.get("/dashboard/summary?date=2026-10-04", headers=ADMIN).json()
    assert b["date"] == "2026-10-04"
    assert [r["rail"] for r in b["rails"]] == ["UPI", "IMPS", "NEFT", "RTGS"]
    assert b["rails"][0] == {"rail": "UPI", "payment_count": 2, "total_paise": 350}
    assert b["rails"][1]["payment_count"] == 0
    assert b["status_counts"] == {
        "CREATED": 1,
        "SUBMITTED": 0,
        "COMPLETED": 0,
        "FAILED": 1,
        "REFUNDED": 0,
    }
    assert [r["state"] for r in b["pending_refunds"]] == ["REQUESTED"]
    assert b["settlement_files"] == []


def test_empty_date_and_default_today(client: TestClient) -> None:
    r = client.get("/dashboard/summary?date=2026-01-01", headers=ADMIN)
    assert r.status_code == 200
    assert all(x["payment_count"] == 0 and x["total_paise"] == 0 for x in r.json()["rails"])
    assert client.get("/dashboard/summary", headers=ADMIN).status_code == 200


def test_settlement_files_listed(client: TestClient, db_path: Path) -> None:
    _ins(
        db_path,
        "p_a",
        "2026-10-04T05:00:00Z",
        state=PaymentState.COMPLETED,
        rail_reference="r",
        submitted_at="2026-10-04T05:00:00Z",
        completed_at="2026-10-04T05:00:00Z",
    )
    client.post("/settlement/run", headers=ADMIN, json={"business_date": "2026-10-04"})
    b = client.get("/dashboard/summary?date=2026-10-04", headers=ADMIN).json()
    assert [f["kind"] for f in b["settlement_files"]] == ["primary"]


@pytest.mark.parametrize("q", ["date=bad", "date=2999-01-01"])
def test_bad_date_422(client: TestClient, q: str) -> None:
    assert client.get(f"/dashboard/summary?{q}", headers=ADMIN).status_code == 422


def test_non_admin_403_and_401(client: TestClient) -> None:
    assert client.get("/dashboard/summary", headers=OPS).status_code == 403
    assert client.get("/dashboard/summary", headers=C1).status_code == 403
    assert client.get("/dashboard/summary").status_code == 401
