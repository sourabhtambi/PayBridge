# ruff: noqa: F811
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.service.settlement_scheduler import SettlementScheduler, next_run
from paybridge.types.enums import PaymentState
from tests.api.test_e5_s1 import ADMIN, C1, OPS, _pay, db_path  # noqa: F401
from tests.support.fake_clock import FakeClock


@pytest.fixture
def client(db_path: Path, tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(db_path=db_path, settlement_dir=tmp_path / "settlement")
    with TestClient(create_app(settings, FakeClock())) as c:
        yield c


DATE = "2026-10-04"


def test_next_run_is_2359_ist() -> None:
    assert next_run(datetime(2026, 10, 4, 9, 30, tzinfo=UTC)).isoformat() == (
        "2026-10-04T23:59:00+05:30"
    )
    assert next_run(datetime(2026, 10, 4, 18, 29, 0, tzinfo=UTC)).isoformat() == (
        "2026-10-05T23:59:00+05:30"
    )


def test_scheduler_fires_once_per_day() -> None:
    clock = FakeClock(datetime(2026, 10, 4, 9, 30, tzinfo=UTC))
    runs: list[str] = []
    s = SettlementScheduler(clock, runs.append)
    assert not s.tick()
    clock.advance(9 * 3600)  # 18:30Z = 00:00 IST Oct 5, past 23:59 Oct 4
    assert s.tick()
    assert not s.tick()
    clock.advance(24 * 3600)
    assert s.tick()
    assert runs == ["2026-10-04", "2026-10-05"]


# AC-07
def test_run_primary_then_repeat(client: TestClient, db_path: Path) -> None:
    _pay(db_path, "pay_a", PaymentState.COMPLETED)
    r = client.post("/settlement/run", headers=ADMIN, json={"business_date": DATE})
    assert r.status_code == 201
    assert r.json()["file"]["kind"] == "primary"
    r2 = client.post("/settlement/run", headers=ADMIN, json={"business_date": DATE})
    assert r2.status_code == 200
    assert r2.json()["file"] is None
    assert "exists" in r2.json()["message"]
    _pay(db_path, "pay_b", PaymentState.COMPLETED)
    r3 = client.post("/settlement/run", headers=ADMIN, json={"business_date": DATE})
    assert (r3.status_code, r3.json()["file"]["kind"]) == (200, "followup")


def test_run_default_date_no_body(client: TestClient) -> None:
    r = client.post("/settlement/run", headers=ADMIN)
    assert r.status_code == 201
    assert r.json()["file"]["business_date"] == DATE


def test_run_bad_dates_422(client: TestClient) -> None:
    for d in ("nope", "2099-01-01", 5):
        r = client.post("/settlement/run", headers=ADMIN, json={"business_date": d})
        assert r.status_code == 422


def test_list_and_download(client: TestClient, db_path: Path) -> None:
    _pay(db_path, "pay_a", PaymentState.COMPLETED)
    fid = client.post("/settlement/run", headers=ADMIN, json={}).json()["file"]["id"]
    items = client.get("/settlement/files", headers=ADMIN).json()["items"]
    assert set(items[0]) >= {"id", "business_date", "kind", "row_count", "checksum"}
    assert items[0]["row_count"] == 1
    assert client.get(f"/settlement/files?business_date={DATE}", headers=ADMIN).json()["total"] == 1
    assert (
        client.get("/settlement/files?business_date=2020-01-01", headers=ADMIN).json()["total"] == 0
    )
    d = client.get(f"/settlement/files/{fid}", headers=ADMIN)
    assert d.status_code == 200
    assert d.headers["content-type"].startswith("text/csv")
    assert "# row_count=1" in d.text and "pay_a" in d.text
    assert client.get("/settlement/files/stl_nope", headers=ADMIN).status_code == 404


def test_non_admin_403(client: TestClient) -> None:
    for h in (C1, OPS):
        assert client.post("/settlement/run", headers=h).status_code == 403
        assert client.get("/settlement/files", headers=h).status_code == 403
        assert client.get("/settlement/files/x", headers=h).status_code == 403
