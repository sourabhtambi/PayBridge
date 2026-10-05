from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from tests.support.fake_clock import FakeClock

C1 = {"X-Role": "customer", "X-Customer-Id": "cus_001"}
C2 = {"X-Role": "customer", "X-Customer-Id": "cus_002"}
OPS = {"X-Role": "ops"}
ADM = {"X-Role": "admin"}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())) as c:
        yield c


def _post(
    c: TestClient, key: str = "k1", amount: object = 5000, h: dict[str, str] = C1
) -> Response:
    return c.post(
        "/payments",
        json={"amount_paise": amount, "beneficiary": "Ravi"},
        headers={**h, "Idempotency-Key": key},
    )


# AC-01
def test_create_and_replay_and_conflict(client: TestClient) -> None:
    r = _post(client)
    assert r.status_code == 202
    b = r.json()
    assert (b["state"], b["rail"], b["amount_paise"]) == ("CREATED", "UPI", 5000)
    r2 = _post(client)
    assert r2.status_code == 200 and r2.json()["id"] == b["id"]
    assert r2.headers["Idempotent-Replay"] == "true"
    assert _post(client, amount=6000).status_code == 409


# AC-01
def test_validation_errors(client: TestClient) -> None:
    r = _post(client, amount=99)
    assert r.status_code == 422
    assert r.json()["error"]["fields"][0]["field"] == "amount_paise"
    assert _post(client, amount="x").status_code == 422
    r = client.post("/payments", json={"amount_paise": 500, "beneficiary": "a"}, headers=C1)
    assert r.status_code == 422
    assert r.json()["error"]["fields"][0]["field"] == "Idempotency-Key"
    r = client.post(
        "/payments",
        json={"amount_paise": 500, "beneficiary": " "},
        headers={**C1, "Idempotency-Key": "z"},
    )
    assert r.json()["error"]["fields"][0]["field"] == "beneficiary"


@pytest.mark.parametrize("h", [OPS, ADM])
def test_ops_admin_cannot_create(client: TestClient, h: dict[str, str]) -> None:
    assert _post(client, h=h).status_code == 403


def test_detail_scoping(client: TestClient) -> None:
    pid = _post(client).json()["id"]
    r = client.get(f"/payments/{pid}", headers=C1)
    assert r.status_code == 200
    assert r.json()["events"][0]["type"] and r.json()["attempts"] == []
    assert client.get(f"/payments/{pid}", headers=C2).status_code == 404
    assert client.get(f"/payments/{pid}", headers=OPS).status_code == 200
    assert client.get(f"/payments/{pid}", headers=ADM).status_code == 200
    assert client.get("/payments/pay_nope", headers=ADM).status_code == 404


def test_list(client: TestClient) -> None:
    a = _post(client, "a").json()["id"]
    b = _post(client, "b").json()["id"]
    _post(client, "c", h=C2)
    ids = [p["id"] for p in client.get("/payments", headers=C1).json()["items"]]
    assert sorted(ids) == sorted([a, b])
    assert client.get("/payments", headers=OPS).json()["total"] == 3
    assert client.get("/payments?customer_id=cus_002", headers=ADM).json()["total"] == 1
    assert client.get("/payments?state=CREATED", headers=C1).json()["total"] == 2
    assert client.get("/payments?state=COMPLETED", headers=C1).json()["total"] == 0
    assert client.get("/payments?state=bogus", headers=C1).status_code == 422
