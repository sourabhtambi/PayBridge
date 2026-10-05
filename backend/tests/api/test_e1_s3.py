from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from paybridge.api.app import create_app
from paybridge.config.settings import Settings
from tests.support.fake_clock import FakeClock


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())
    with TestClient(app) as c:
        yield c


def test_health_ok_without_headers(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_503_when_db_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import sqlite3

    def boom(*_: object) -> None:
        raise sqlite3.OperationalError("down")

    monkeypatch.setattr(client.app.state.container.db, "connect", boom)  # type: ignore[attr-defined]
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "error", "database": "error"}


@pytest.mark.parametrize("headers", [{}, {"X-Role": "hacker"}])
def test_missing_or_unknown_role_401(client: TestClient, headers: dict[str, str]) -> None:
    r = client.get("/admin/simulation", headers=headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("extra", [{}, {"X-Customer-Id": "cus_999"}, {"X-Customer-Id": "ops_001"}])
def test_customer_requires_valid_id(client: TestClient, extra: dict[str, str]) -> None:
    r = client.get("/admin/simulation", headers={"X-Role": "customer", **extra})
    assert r.status_code == 401


def test_valid_customer_resolves_then_forbidden(client: TestClient) -> None:
    r = client.get("/admin/simulation", headers={"X-Role": "customer", "X-Customer-Id": "cus_001"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_ops_forbidden_admin_allowed(client: TestClient) -> None:
    assert client.get("/admin/simulation", headers={"X-Role": "ops"}).status_code == 403
    assert client.get("/admin/simulation", headers={"X-Role": "admin"}).status_code == 200


def test_customers_lists_all_roles(client: TestClient) -> None:
    body = client.get("/customers").json()
    assert body["total"] == 5
    assert {i["role"] for i in body["items"]} == {"customer", "ops", "admin"}
    assert set(body["items"][0]) == {"id", "name", "role"}


def test_cors_preflight(client: TestClient) -> None:
    r = client.options(
        "/customers",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Role,X-Customer-Id,Idempotency-Key",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    allowed = r.headers["access-control-allow-headers"].lower()
    for h in ("x-role", "x-customer-id", "idempotency-key"):
        assert h in allowed


def test_unexpected_error_envelope(tmp_path: Path) -> None:
    app = create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("x")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"


def _boom_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(db_path=tmp_path / "t.db"), FakeClock())

    @app.post("/boom")
    def boom() -> None:
        raise RuntimeError("x")

    return TestClient(app, raise_server_exceptions=False)


def test_unexpected_error_carries_cors_headers_for_allowed_origin(tmp_path: Path) -> None:
    """Without them the browser hides the 500 and the UI only shows 'Failed to fetch'."""
    with _boom_client(tmp_path) as c:
        r = c.post("/boom", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "origin" in r.headers["vary"].lower()


def test_unexpected_error_has_no_cors_headers_for_other_origin(tmp_path: Path) -> None:
    with _boom_client(tmp_path) as c:
        r = c.post("/boom", headers={"Origin": "http://evil.example"})
        no_origin = c.post("/boom")
    assert r.status_code == 500 and "access-control-allow-origin" not in r.headers
    assert "access-control-allow-origin" not in no_origin.headers
