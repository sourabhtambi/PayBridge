import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from tests.support.fake_clock import FakeClock

C1 = {"X-Role": "customer", "X-Customer-Id": "cus_001"}
NAME = "Zorbaxian Quillfeather"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    original = logging.getLogRecordFactory()
    with TestClient(create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())) as c:
        yield c
    logging.setLogRecordFactory(original)


def test_full_run_logs_contain_no_beneficiary(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        r = client.post(
            "/payments",
            json={"amount_paise": 5000, "beneficiary": NAME},
            headers={**C1, "Idempotency-Key": "k1"},
        )
        assert r.status_code == 202
        logging.getLogger("paybridge.worker").info("processing %s", NAME)
        logging.getLogger("paybridge.refund").error("refund for %s", NAME)
        try:
            raise RuntimeError(f"rail failed for {NAME}")
        except RuntimeError:
            logging.getLogger("paybridge.worker").exception("failure")
    assert "Zorbaxian" not in caplog.text and "Quillfeather" not in caplog.text
    assert "Z*** Q***" in caplog.text


def test_restart_reloads_names_from_db(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    from paybridge.lib import masking

    original = logging.getLogRecordFactory()
    settings = Settings(db_path=tmp_path / "r.db")
    name = "Yvonne Blorptastic"
    try:
        with TestClient(create_app(settings, FakeClock())) as c:
            r = c.post(
                "/payments",
                json={"amount_paise": 5000, "beneficiary": name},
                headers={**C1, "Idempotency-Key": "k1"},
            )
            assert r.status_code == 202
        masking._registered.clear()
        masking._pattern = None
        with TestClient(create_app(settings, FakeClock())):
            with caplog.at_level(logging.INFO):
                logging.getLogger("x").info("hello %s", name)
        assert "Yvonne" not in caplog.text and "Y*** B***" in caplog.text
    finally:
        logging.setLogRecordFactory(original)


def test_real_flows_never_log_raw_values(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    import time

    name = "Wilhelmina Snorgle"
    admin = {"X-Role": "admin"}
    original = logging.getLogRecordFactory()
    try:
        with caplog.at_level(logging.DEBUG):
            with TestClient(create_app(Settings(db_path=tmp_path / "f.db"), FakeClock())) as c:
                r = c.post(
                    "/payments",
                    json={"amount_paise": 5000, "beneficiary": name},
                    headers={**C1, "Idempotency-Key": "k1"},
                )
                pid = r.json()["id"]
                for _ in range(100):
                    if c.get(f"/payments/{pid}", headers=C1).json()["state"] == "COMPLETED":
                        break
                    time.sleep(0.05)
                else:
                    pytest.fail("payment not completed")
                rid = c.post("/refunds", headers=C1, json={"payment_id": pid}).json()["id"]
                assert c.post(f"/refunds/{rid}/approve", headers=admin).status_code == 200
    finally:
        logging.setLogRecordFactory(original)
    assert "Wilhelmina" not in caplog.text and "Snorgle" not in caplog.text
