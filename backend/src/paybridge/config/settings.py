"""Runtime settings read from the environment."""

import math
import os
from dataclasses import dataclass
from pathlib import Path


class InvalidPollInterval(ValueError):
    """PAYBRIDGE_WORKER_POLL_INTERVAL is not a finite number within 0.05-60."""


class InvalidBusyTimeout(ValueError):
    """PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS is not an integer within 0-600000."""


class InvalidCorsOrigin(ValueError):
    """PAYBRIDGE_CORS_ORIGIN is empty or a wildcard."""


def _poll_interval(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise InvalidPollInterval(f"not a number: {raw!r}") from exc
    if not math.isfinite(value) or not 0.05 <= value <= 60:
        raise InvalidPollInterval(f"must be finite and within 0.05-60: {raw!r}")
    return value


def _busy_timeout(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise InvalidBusyTimeout(f"not an integer: {raw!r}") from exc
    if not 0 <= value <= 600000:
        raise InvalidBusyTimeout(f"must be within 0-600000: {raw!r}")
    return value


def _cors_origin(raw: str) -> str:
    if not raw.strip() or "*" in raw:
        raise InvalidCorsOrigin(f"explicit origin required, got {raw!r}")
    return raw


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("data/paybridge.db")
    rail_ledger_path: Path = Path("data/rail_ledger.jsonl")
    settlement_dir: Path = Path("data/settlement")
    cors_origin: str = "http://localhost:3000"
    busy_timeout_ms: int = 10000
    poll_interval_seconds: float = 0.5
    env: str = "dev"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        d = cls()
        data_dir = Path(env.get("PAYBRIDGE_DATA_DIR", "data"))
        return cls(
            db_path=Path(env.get("PAYBRIDGE_DB_PATH", str(data_dir / "paybridge.db"))),
            rail_ledger_path=Path(
                env.get("PAYBRIDGE_RAIL_LEDGER_PATH", str(data_dir / "rail_ledger.jsonl"))
            ),
            settlement_dir=Path(env.get("PAYBRIDGE_SETTLEMENT_DIR", str(data_dir / "settlement"))),
            cors_origin=_cors_origin(env.get("PAYBRIDGE_CORS_ORIGIN", d.cors_origin)),
            busy_timeout_ms=_busy_timeout(
                env.get("PAYBRIDGE_SQLITE_BUSY_TIMEOUT_MS", str(d.busy_timeout_ms))
            ),
            poll_interval_seconds=_poll_interval(
                env.get("PAYBRIDGE_WORKER_POLL_INTERVAL", str(d.poll_interval_seconds))
            ),
            env=env.get("PAYBRIDGE_ENV", d.env),
        )
