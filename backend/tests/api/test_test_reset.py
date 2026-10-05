from pathlib import Path

from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.types.enums import Rail, SimulationMode
from tests.support.fake_clock import FakeClock

C1 = {"X-Role": "customer", "X-Customer-Id": "cus_001"}
OPS = {"X-Role": "ops"}


def _app(tmp_path: Path, env: str) -> TestClient:
    settings = Settings(db_path=tmp_path / "t.db", settlement_dir=tmp_path / "stl", env=env)
    return TestClient(create_app(settings, FakeClock()))


def test_reset_is_not_available_outside_test_env(tmp_path: Path) -> None:
    with _app(tmp_path, "dev") as client:
        assert client.post("/test/reset").status_code == 404


def test_reset_wipes_state_and_keeps_demo_users(tmp_path: Path) -> None:
    with _app(tmp_path, "test") as client:
        r = client.post(
            "/payments",
            json={"amount_paise": 5000, "beneficiary": "Ravi"},
            headers={**C1, "Idempotency-Key": "k1"},
        )
        assert r.status_code == 202
        (tmp_path / "stl").mkdir(exist_ok=True)
        (tmp_path / "stl" / "old.csv").write_text("x")
        client.app.state.simulation.set(Rail.UPI, SimulationMode.TRANSIENT, None, 0.5)  # type: ignore[attr-defined]

        assert client.post("/test/reset").status_code == 200

        assert client.get("/payments", headers=OPS).json()["total"] == 0
        assert len(client.get("/customers").json()["items"]) == 5
        assert not list((tmp_path / "stl").glob("*"))
        sim = client.app.state.simulation.get(Rail.UPI)  # type: ignore[attr-defined]
        assert sim.mode is SimulationMode.SUCCESS
        # still usable, including the append-only event triggers
        again = client.post(
            "/payments",
            json={"amount_paise": 5000, "beneficiary": "Ravi"},
            headers={**C1, "Idempotency-Key": "k1"},
        )
        assert again.status_code == 202
