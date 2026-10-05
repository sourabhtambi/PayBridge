# ruff: noqa: F811
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.types.enums import PaymentState
from tests.api.test_e5_s1 import ADMIN, C1, OPS, _events, _pay, client, db_path  # noqa: F401


def _refund(client: TestClient, db_path: Path, pid: str) -> str:
    _pay(db_path, pid, PaymentState.COMPLETED)
    return str(client.post("/refunds", headers=C1, json={"payment_id": pid}).json()["id"])


# AC-08
def test_approve_executes(client: TestClient, db_path: Path) -> None:
    rid = _refund(client, db_path, "pay_a")
    r = client.post(f"/refunds/{rid}/approve", headers=ADMIN)
    assert r.status_code == 200
    assert (r.json()["state"], r.json()["decided_by"]) == ("EXECUTED", "adm_001")
    assert _events(db_path, "pay_a")[-2:] == ["REFUND_EXECUTED", "PAYMENT_REFUNDED"]


# AC-08
def test_approve_moves_original_payment_to_refunded(client: TestClient, db_path: Path) -> None:
    rid = _refund(client, db_path, "pay_r")
    assert client.get("/payments/pay_r", headers=C1).json()["state"] == "COMPLETED"
    client.post(f"/refunds/{rid}/approve", headers=ADMIN)
    assert client.get("/payments/pay_r", headers=C1).json()["state"] == "REFUNDED"


def test_reject(client: TestClient, db_path: Path) -> None:
    rid = _refund(client, db_path, "pay_b")
    r = client.post(f"/refunds/{rid}/reject", headers=ADMIN)
    b = r.json()
    assert (b["state"], b["reason_code"], b["decided_by"]) == (
        "REJECTED",
        "REJECTED_BY_ADMIN",
        "adm_001",
    )
    assert client.get("/payments/pay_b", headers=C1).json()["state"] == "COMPLETED"


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_already_decided_409(client: TestClient, db_path: Path, action: str) -> None:
    rid = _refund(client, db_path, "pay_c")
    client.post(f"/refunds/{rid}/reject", headers=ADMIN)
    r = client.post(f"/refunds/{rid}/{action}", headers=ADMIN)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "REFUND_ALREADY_DECIDED")


def test_concurrent_approvals(client: TestClient, db_path: Path) -> None:
    rid = _refund(client, db_path, "pay_d")
    with ThreadPoolExecutor(2) as ex:
        codes = sorted(
            f.result().status_code
            for f in [
                ex.submit(client.post, f"/refunds/{rid}/approve", headers=ADMIN) for _ in range(2)
            ]
        )
    assert codes == [200, 409]


def test_permanent_failure(client: TestClient, db_path: Path) -> None:
    rid = _refund(client, db_path, "pay_e")
    client.put(
        "/admin/simulation/UPI",
        headers=ADMIN,
        json={"mode": "permanent_failure", "reason_code": "LIMIT_EXCEEDED"},
    )
    r = client.post(f"/refunds/{rid}/approve", headers=ADMIN)
    assert (r.json()["state"], r.json()["reason_code"]) == ("FAILED", "LIMIT_EXCEEDED")
    assert client.get("/payments/pay_e", headers=C1).json()["state"] == "COMPLETED"
    assert client.post(f"/refunds/{rid}/approve", headers=ADMIN).status_code == 409


@pytest.mark.parametrize("headers", [C1, OPS])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_forbidden(client: TestClient, db_path: Path, headers: dict[str, str], action: str) -> None:
    rid = _refund(client, db_path, "pay_f")
    assert client.post(f"/refunds/{rid}/{action}", headers=headers).status_code == 403


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_unknown_404(client: TestClient, action: str) -> None:
    assert client.post(f"/refunds/rfd_x/{action}", headers=ADMIN).status_code == 404
