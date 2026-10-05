import pytest

from paybridge.config.settings import (
    InvalidBusyTimeout,
    InvalidCorsOrigin,
    InvalidPollInterval,
    Settings,
)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("PAYBRIDGE_WORKER_POLL_INTERVAL", "PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS"):
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env()
    assert s.poll_interval_seconds == 0.5
    assert s.busy_timeout_ms == 10000


def test_valid_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYBRIDGE_WORKER_POLL_INTERVAL", "0.05")
    monkeypatch.setenv("PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS", "600000")
    monkeypatch.setenv("PAYBRIDGE_CORS_ORIGIN", "http://x.test")
    s = Settings.from_env()
    assert (s.poll_interval_seconds, s.busy_timeout_ms, s.cors_origin) == (
        0.05,
        600000,
        "http://x.test",
    )


@pytest.mark.parametrize("v", ["0.04", "60.1", "nan", "inf", "-inf", "abc"])
def test_bad_poll(monkeypatch: pytest.MonkeyPatch, v: str) -> None:
    monkeypatch.setenv("PAYBRIDGE_WORKER_POLL_INTERVAL", v)
    with pytest.raises(InvalidPollInterval):
        Settings.from_env()


@pytest.mark.parametrize("v", ["-1", "600001", "1.5", "abc"])
def test_bad_busy(monkeypatch: pytest.MonkeyPatch, v: str) -> None:
    monkeypatch.setenv("PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS", v)
    with pytest.raises(InvalidBusyTimeout):
        Settings.from_env()


@pytest.mark.parametrize("v", ["*", "", "http://*.x.test"])
def test_bad_cors(monkeypatch: pytest.MonkeyPatch, v: str) -> None:
    monkeypatch.setenv("PAYBRIDGE_CORS_ORIGIN", v)
    with pytest.raises(InvalidCorsOrigin):
        Settings.from_env()
