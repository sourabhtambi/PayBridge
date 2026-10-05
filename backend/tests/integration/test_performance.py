"""E9-S2: NFR-01/NFR-02 load checks (F132-F134) against the real app on temp SQLite."""

import logging
import math
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from paybridge.lib.clock import SystemClock

HEADERS = {"X-Role": "customer", "X-Customer-Id": "cus_001"}
TERMINAL = ("COMPLETED", "FAILED")


@pytest.fixture
def perf(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    db = tmp_path / "perf.db"
    app = create_app(Settings(db_path=db, poll_interval_seconds=0.05), SystemClock())
    with TestClient(app) as client:
        yield client, db


def _post(client: TestClient, key: str) -> tuple[int, float]:
    start = time.perf_counter()
    r = client.post(
        "/payments",
        json={"amount_paise": 5000, "beneficiary": "Ravi"},
        headers={**HEADERS, "Idempotency-Key": key},
    )
    return r.status_code, (time.perf_counter() - start) * 1000


def _states(db: Path) -> list[str]:
    conn = sqlite3.connect(db)
    try:
        return [row[0] for row in conn.execute("SELECT state FROM payments")]
    finally:
        conn.close()


def test_f132_post_p95_latency(perf: tuple[TestClient, Path]) -> None:
    client, _ = perf
    results = [_post(client, f"lat-{i}") for i in range(200)]
    assert all(status == 202 for status, _ in results)
    latencies = sorted(ms for _, ms in results)
    p95 = latencies[math.ceil(0.95 * len(latencies)) - 1]
    assert p95 <= 300, f"p95={p95:.1f}ms"


def test_f133_f134_sustained_throughput_and_terminal(
    perf: tuple[TestClient, Path], caplog: pytest.LogCaptureFixture
) -> None:
    client, db = perf
    caplog.set_level(logging.DEBUG)
    statuses: list[int] = []
    begin = time.perf_counter()
    for i in range(200):
        delay = begin + i / 20 - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        statuses.append(_post(client, f"load-{i}")[0])
    elapsed = time.perf_counter() - begin
    assert elapsed <= 11, f"could not sustain 20/s: {elapsed:.1f}s"
    assert all(200 <= s < 300 for s in statuses)
    assert len(_states(db)) == 200

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and not all(s in TERMINAL for s in _states(db)):
        time.sleep(0.25)
    assert all(s in TERMINAL for s in _states(db))
    assert "database is locked" not in caplog.text
