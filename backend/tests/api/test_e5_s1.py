import json
import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.repository.db import Database
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.types.enums import PaymentState
from tests.support.factories import TS, make_payment
from tests.support.fake_clock import FakeClock

C1 = {"X-Role": "customer", "X-Customer-Id": "cus_001"}
C2 = {"X-Role": "customer", "X-Customer-Id": "cus_002"}
ADMIN = {"X-Role": "admin"}
OPS = {"X-Role": "ops"}


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(db_path=db_path), FakeClock())) as c:
        yield c


def _pay(db_path: Path, pid: str, state: PaymentState, cust: str = "cus_001") -> str:
    extra: dict[str, object] = {}
    if state is PaymentState.COMPLETED:
        extra = {"rail_reference": "ref1", "completed_at": TS, "submitted_at": TS}
    elif state is PaymentState.FAILED:
        extra = {"reason_code": "INSUFFICIENT_FUNDS"}
    with Database(db_path).write() as conn:
        PaymentsRepo(conn).insert(
            make_payment(id=pid, state=state, customer_id=cust, idempotency_key=pid, **extra)
        )
    return pid


def _events(db_path: Path, pid: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT type FROM payment_events WHERE payment_id=?", (pid,)).fetchall()
    conn.close()
    return [r[0] for r in rows]


# AC-08, AC-09
def test_create_refund_201_and_event(client: TestClient, db_path: Path) -> None:
    pid = _pay(db_path, "pay_a", PaymentState.COMPLETED)
    r = client.post("/refunds", headers=C1, json={"payment_id": pid})
    assert r.status_code == 201
    b = r.json()
    assert (b["state"], b["amount_paise"], b["requested_by"]) == ("REQUESTED", 10000, "cus_001")
    assert _events(db_path, pid) == ["REFUND_REQUESTED"]


@pytest.mark.parametrize(
    "state", [PaymentState.CREATED, PaymentState.SUBMITTED, PaymentState.FAILED]
)
# AC-08
def test_non_refundable_422(client: TestClient, db_path: Path, state: PaymentState) -> None:
    pid = _pay(db_path, "pay_b", state)
    r = client.post("/refunds", headers=C1, json={"payment_id": pid})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PAYMENT_NOT_REFUNDABLE"


def test_duplicate_409(client: TestClient, db_path: Path) -> None:
    pid = _pay(db_path, "pay_c", PaymentState.COMPLETED)
    assert client.post("/refunds", headers=C1, json={"payment_id": pid}).status_code == 201
    r = client.post("/refunds", headers=C1, json={"payment_id": pid})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "REFUND_ALREADY_EXISTS")


def test_concurrent_creates_one(client: TestClient, db_path: Path) -> None:
    pid = _pay(db_path, "pay_d", PaymentState.COMPLETED)
    with ThreadPoolExecutor(10) as ex:
        codes = list(
            ex.map(
                lambda _: client.post("/refunds", headers=C1, json={"payment_id": pid}).status_code,
                range(10),
            )
        )
    assert codes.count(201) == 1 and codes.count(409) == 9
    assert _events(db_path, pid) == ["REFUND_REQUESTED"]


def test_other_customer_404_and_roles_403(client: TestClient, db_path: Path) -> None:
    pid = _pay(db_path, "pay_e", PaymentState.COMPLETED)
    assert client.post("/refunds", headers=C2, json={"payment_id": pid}).status_code == 404
    assert client.post("/refunds", headers=C1, json={"payment_id": "nope"}).status_code == 404
    for h in (OPS, ADMIN):
        assert client.post("/refunds", headers=h, json={"payment_id": pid}).status_code == 403


def test_missing_payment_id_422(client: TestClient) -> None:
    r = client.post("/refunds", headers=C1, json={})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


# AC-10
def test_list_by_role_and_filter(client: TestClient, db_path: Path) -> None:
    p1 = _pay(db_path, "pay_f", PaymentState.COMPLETED)
    p2 = _pay(db_path, "pay_g", PaymentState.COMPLETED, "cus_002")
    client.post("/refunds", headers=C1, json={"payment_id": p1})
    client.post("/refunds", headers=C2, json={"payment_id": p2})
    mine = client.get("/refunds", headers=C1).json()
    assert [i["payment_id"] for i in mine["items"]] == [p1]
    assert client.get("/refunds", headers=ADMIN).json()["total"] == 2
    assert client.get("/refunds?state=REQUESTED", headers=ADMIN).json()["total"] == 2
    assert client.get("/refunds?state=EXECUTED", headers=ADMIN).json()["total"] == 0
    assert client.get("/refunds?state=BAD", headers=ADMIN).status_code == 422
    assert json.dumps(mine)
