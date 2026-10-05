import hashlib
import sqlite3
from pathlib import Path

import pytest

from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.settlement_repo import SettlementRepo
from paybridge.service.settlement_service import SettlementService
from paybridge.types.enums import PaymentState, Rail, ReconStatus, SettlementKind
from paybridge.types.models import ReconciliationResult
from tests.support.factories import TS, make_payment
from tests.support.fake_clock import FakeClock

DATE = "2026-10-04"


def _svc(conn: sqlite3.Connection, clock: FakeClock, tmp_path: Path) -> SettlementService:
    return SettlementService(
        PaymentsRepo(conn), ReconRepo(conn), SettlementRepo(conn), clock, tmp_path / "s"
    )


def _add(conn: sqlite3.Connection, n: int, completed_at: str) -> None:
    PaymentsRepo(conn).insert(
        make_payment(
            id=f"pay_{n:012d}",
            idempotency_key=f"k{n}",
            state=PaymentState.COMPLETED,
            completed_at=completed_at,
            rail_reference=f"REF{n}",
        )
    )


def _recon(conn: sqlite3.Connection, n: int, status: ReconStatus) -> None:
    ReconRepo(conn).insert(
        ReconciliationResult(
            id=f"rec_{n:012d}",
            statement_date=DATE,
            rail=Rail.UPI,
            status=status,
            payment_id=f"pay_{n:012d}",
            payment_ref=f"REF{n}",
            created_at=TS,
            updated_at=TS,
        )
    )


def test_ist_boundaries_and_columns(
    conn: sqlite3.Connection, clock: FakeClock, tmp_path: Path
) -> None:
    _add(conn, 1, "2026-10-04T18:29:59Z")
    _add(conn, 2, "2026-10-04T18:30:00Z")
    _add(conn, 3, "2026-10-03T18:30:00Z")
    rec = _svc(conn, clock, tmp_path).run(DATE)
    assert rec is not None
    lines = Path(rec.path).read_text().splitlines()
    assert lines[0] == "payment_id,rail,amount_paise,rail_ref,recon_status,unmatched_flag"
    assert [ln.split(",")[0] for ln in lines[1:-2]] == ["pay_000000000003", "pay_000000000001"]


# AC-07
def test_unmatched_included_footer_and_record(
    conn: sqlite3.Connection, clock: FakeClock, tmp_path: Path
) -> None:
    _add(conn, 1, "2026-10-04T05:00:00Z")
    _add(conn, 2, "2026-10-04T06:00:00Z")
    _add(conn, 3, "2026-10-04T07:00:00Z")
    _recon(conn, 1, ReconStatus.MATCHED)
    _recon(conn, 2, ReconStatus.AMOUNT_MISMATCH)
    rec = _svc(conn, clock, tmp_path).run(DATE)
    assert rec is not None and rec.kind is SettlementKind.PRIMARY and rec.row_count == 3
    lines = Path(rec.path).read_text().splitlines()
    assert lines[1].endswith("matched,false")
    assert lines[2].endswith("amount_mismatch,true")
    assert lines[3].endswith("unmatched_internal,true")
    data = "".join(ln + "\n" for ln in lines[1:4])
    digest = hashlib.sha256(data.encode()).hexdigest()
    assert lines[-2:] == ["# row_count=3", f"# sha256={digest}"]
    assert rec.checksum == digest
    assert SettlementRepo(conn).get(rec.id) == rec


def test_rerun_does_not_overwrite_and_followup(
    conn: sqlite3.Connection, clock: FakeClock, tmp_path: Path
) -> None:
    _add(conn, 1, "2026-10-04T05:00:00Z")
    svc = _svc(conn, clock, tmp_path)
    primary = svc.run(DATE)
    assert primary is not None
    before = Path(primary.path).read_bytes()
    assert svc.run(DATE) is None
    assert Path(primary.path).read_bytes() == before
    assert len(SettlementRepo(conn).list_by_date(DATE)) == 1
    _add(conn, 2, "2026-10-04T08:00:00Z")
    follow = svc.run(DATE)
    assert follow is not None and follow.kind is SettlementKind.FOLLOWUP
    assert follow.sequence == 1 and follow.row_count == 1
    assert "pay_000000000002" in Path(follow.path).read_text()
    assert "pay_000000000001" not in Path(follow.path).read_text()
    assert Path(primary.path).read_bytes() == before
    assert svc.run(DATE) is None


def test_empty_primary_allowed(conn: sqlite3.Connection, clock: FakeClock, tmp_path: Path) -> None:
    rec = _svc(conn, clock, tmp_path).run(DATE)
    assert rec is not None and rec.row_count == 0


# AC-07
def test_write_once_refuses_existing(tmp_path: Path) -> None:
    from paybridge.service.settlement_service import _write_once

    p = tmp_path / "a.csv"
    _write_once(p, "x")
    with pytest.raises(FileExistsError):
        _write_once(p, "y")
    assert p.read_text() == "x" and not (tmp_path / "a.csv.tmp").exists()
