import re
from datetime import UTC

from paybridge.config import constants
from paybridge.config.rails import RAIL_SETTINGS
from paybridge.lib import ids
from paybridge.lib.clock import SystemClock
from paybridge.types.enums import Rail, SimulationMode


def test_id_generators_use_prefix_and_12_hex() -> None:
    cases = {
        ids.new_payment_id: "pay_",
        ids.new_refund_id: "rfd_",
        ids.new_reconciliation_id: "rec_",
        ids.new_settlement_id: "stl_",
        ids.new_event_id: "evt_",
        ids.new_statement_entry_id: "rse_",
    }
    for factory, prefix in cases.items():
        value = factory()
        assert re.fullmatch(prefix + r"[0-9a-f]{12}", value)
        assert factory() != value


def test_system_clock_is_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_constants() -> None:
    assert constants.IDEMPOTENCY_TTL_SECONDS == 86400
    assert constants.RETRY_MAX_ATTEMPTS == 5
    assert constants.RETRY_BASE_DELAY_SECONDS == 1
    assert constants.STUCK_THRESHOLD_SECONDS == 300
    assert constants.STUCK_SCAN_INTERVAL_SECONDS == 30
    assert constants.OUTBOX_LEASE_SECONDS == 60
    assert constants.BUSINESS_TZ == "Asia/Kolkata"
    assert constants.SETTLEMENT_CUTOFF == "23:59"


def test_rail_settings_cover_every_rail() -> None:
    assert set(RAIL_SETTINGS) == set(Rail)
    for rail, cfg in RAIL_SETTINGS.items():
        assert cfg.reference_prefix == rail.value
        assert cfg.supported_modes == frozenset(SimulationMode)
