import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.service.rail_adapters import build_adapters
from paybridge.service.simulation import SimulationStore
from paybridge.types.enums import Rail, SimulationMode
from paybridge.types.errors import PermanentRailError, TransientRailError
from tests.support.fake_clock import FakeClock

ADMIN = {"X-Role": "admin"}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())) as c:
        yield c


def test_get_defaults_all_rails_success(client: TestClient) -> None:
    body = client.get("/admin/simulation", headers=ADMIN).json()
    assert body["total"] == 4
    assert {i["mode"] for i in body["items"]} == {"success"}


def test_put_echo_and_persist(client: TestClient) -> None:
    r = client.put(
        "/admin/simulation/UPI",
        headers=ADMIN,
        json={"mode": "permanent_failure", "reason_code": "INSUFFICIENT_FUNDS"},
    )
    assert r.status_code == 200
    assert r.json() == {
        "rail": "UPI",
        "mode": "permanent_failure",
        "reason_code": "INSUFFICIENT_FUNDS",
        "transient_failure_rate": 0,
    }
    items = client.get("/admin/simulation", headers=ADMIN).json()["items"]
    assert [i["mode"] for i in items].count("permanent_failure") == 1
    t = client.put(
        "/admin/simulation/NEFT",
        headers=ADMIN,
        json={"mode": "transient", "transient_failure_rate": 0.5},
    )
    assert t.json()["transient_failure_rate"] == 0.5


@pytest.mark.parametrize(
    "body",
    [
        {"mode": "transient", "transient_failure_rate": 1.5},
        {"mode": "transient"},
        {"mode": "permanent_failure"},
        {"mode": "permanent_failure", "reason_code": "BOGUS"},
    ],
)
def test_put_validation_422(client: TestClient, body: dict[str, object]) -> None:
    assert client.put("/admin/simulation/UPI", headers=ADMIN, json=body).status_code == 422


def test_put_unknown_rail_404(client: TestClient) -> None:
    r = client.put("/admin/simulation/XYZ", headers=ADMIN, json={"mode": "success"})
    assert r.status_code == 404


@pytest.mark.parametrize("role", ["customer", "ops"])
def test_non_admin_403(client: TestClient, role: str) -> None:
    h = {"X-Role": role, "X-Customer-Id": "cus_001"}
    assert client.get("/admin/simulation", headers=h).status_code == 403
    assert (
        client.put("/admin/simulation/UPI", headers=h, json={"mode": "success"}).status_code == 403
    )


def test_adapter_permanent_failure_carries_reason() -> None:
    sim = SimulationStore(seed=1)
    sim.set(Rail.UPI, SimulationMode.PERMANENT_FAILURE, "LIMIT_EXCEEDED", None)
    adapter = build_adapters(FakeClock(), sim)[Rail.UPI]
    with pytest.raises(PermanentRailError) as e:
        asyncio.run(adapter.submit("pay_1", 100))
    assert e.value.reason_code == "LIMIT_EXCEEDED"


def test_adapter_transient_rates_seeded() -> None:
    sim = SimulationStore(seed=42)
    adapter = build_adapters(FakeClock(), sim)[Rail.IMPS]
    sim.set(Rail.IMPS, SimulationMode.TRANSIENT, None, 1.0)
    for i in range(100):
        with pytest.raises(TransientRailError):
            asyncio.run(adapter.submit(f"p{i}", 100))
    sim.set(Rail.IMPS, SimulationMode.TRANSIENT, None, 0.0)
    for i in range(100):
        asyncio.run(adapter.submit(f"q{i}", 100))
