# ruff: noqa: F811
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.container import Container  # noqa: F401
from paybridge.repository.db import Database
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.types.enums import PaymentState, Rail
from paybridge.types.models import RailStatementEntry
from tests.api.test_e5_s1 import ADMIN, C1, OPS, _pay, client, db_path  # noqa: F401
from tests.support.factories import TS

DATE = "2026-10-04"


def _seed(client: TestClient, db_path: Path) -> list[dict[str, object]]:
    _pay(db_path, "pay_a", PaymentState.COMPLETED)
    with Database(db_path).write() as conn:
        StatementsRepo(conn).insert_or_ignore(
            RailStatementEntry(
                id="stm_x",
                rail=Rail.NEFT,
                payment_ref="ghost",
                payment_id=None,
                amount_paise=500,
                statement_date=DATE,
                created_at=TS,
            )
        )
    r = client.post("/reconciliation/run", headers=OPS, json={"statement_date": DATE})
    assert r.status_code == 200
    items: list[dict[str, object]] = client.get("/reconciliation/unmatched", headers=OPS).json()[
        "items"
    ]
    return items


def test_run_counts_and_idempotent(client: TestClient, db_path: Path) -> None:
    _seed(client, db_path)
    r = client.post("/reconciliation/run", headers=ADMIN, json={"statement_date": DATE})
    assert r.json()["counts"] == {
        "matched": 1,
        "unmatched_internal": 0,
        "unmatched_external": 1,
        "amount_mismatch": 0,
    }


@pytest.mark.parametrize("d", ["nope", "2026-13-01", "2099-01-01", "20261004"])
def test_run_bad_date_422(client: TestClient, d: str) -> None:
    r = client.post("/reconciliation/run", headers=OPS, json={"statement_date": d})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


def test_run_missing_body_422(client: TestClient) -> None:
    assert client.post("/reconciliation/run", headers=OPS, json={}).status_code == 422


# AC-06, AC-10
def test_unmatched_filters(client: TestClient, db_path: Path) -> None:
    items = _seed(client, db_path)
    assert [i["status"] for i in items] == ["unmatched_external"]
    q = client.get
    assert q("/reconciliation/unmatched?status=matched", headers=OPS).json()["items"] == []
    assert q("/reconciliation/unmatched?rail=UPI", headers=OPS).json()["items"] == []
    assert len(q("/reconciliation/unmatched?rail=NEFT", headers=OPS).json()["items"]) == 1
    url = f"/reconciliation/unmatched?statement_date={DATE}"
    assert len(q(url, headers=OPS).json()["items"]) == 1
    assert (
        q("/reconciliation/unmatched?statement_date=2020-01-01", headers=OPS).json()["total"] == 0
    )
    for bad in ("status=x", "rail=x", "statement_date=x"):
        assert q(f"/reconciliation/unmatched?{bad}", headers=OPS).status_code == 422


def test_resolve_flow_and_no_side_effects(client: TestClient, db_path: Path) -> None:
    rid = str(_seed(client, db_path)[0]["id"])
    before = sqlite3.connect(db_path).execute("SELECT * FROM payments").fetchall()
    r = client.post(f"/reconciliation/{rid}/resolve", headers=OPS, json={"note": " checked "})
    b = r.json()
    assert (r.status_code, b["resolved"], b["resolution_note"], b["resolved_by"]) == (
        200,
        True,
        "checked",
        "ops_001",
    )
    assert b["statement_amount_paise"] == 500
    assert sqlite3.connect(db_path).execute("SELECT * FROM payments").fetchall() == before
    assert client.get("/reconciliation/unmatched", headers=OPS).json()["items"] == []
    again = client.post(f"/reconciliation/{rid}/resolve", headers=ADMIN, json={"note": "x"})
    assert (again.status_code, again.json()["error"]["code"]) == (409, "RECON_ALREADY_RESOLVED")


def test_resolve_validation_and_404(client: TestClient, db_path: Path) -> None:
    rid = str(_seed(client, db_path)[0]["id"])
    for note in ("", "   ", "x" * 501):
        r = client.post(f"/reconciliation/{rid}/resolve", headers=OPS, json={"note": note})
        assert r.status_code == 422
    assert client.post(f"/reconciliation/{rid}/resolve", headers=OPS, json={}).status_code == 422
    r = client.post("/reconciliation/nope/resolve", headers=OPS, json={"note": "x"})
    assert r.status_code == 404


def test_resolve_matched_422(client: TestClient, db_path: Path) -> None:
    _seed(client, db_path)
    with Database(db_path).read() as conn:
        matched = [r for r in ReconRepo(conn).list_by_date(DATE) if r.status.value == "matched"]
    r = client.post(f"/reconciliation/{matched[0].id}/resolve", headers=OPS, json={"note": "x"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("POST", "/reconciliation/run"),
        ("GET", "/reconciliation/unmatched"),
        ("POST", "/reconciliation/x/resolve"),
    ],
)
def test_customer_403_and_unauth_401(client: TestClient, method: str, url: str) -> None:
    body = {"statement_date": DATE, "note": "x"}
    assert client.request(method, url, headers=C1, json=body).status_code == 403
    assert client.request(method, url, json=body).status_code == 401
