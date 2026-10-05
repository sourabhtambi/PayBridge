"""Builds append-only settlement CSVs per IST business date."""

import hashlib
import os
from pathlib import Path

from paybridge.lib.ids import new_settlement_id
from paybridge.lib.timeutil import iso_z, ist_day_bounds_utc
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.settlement_repo import SettlementRepo
from paybridge.types.enums import ReconStatus, SettlementKind
from paybridge.types.models import Payment, SettlementFile
from paybridge.types.ports import Clock

HEADER = "payment_id,rail,amount_paise,rail_ref,recon_status,unmatched_flag\n"


class SettlementService:
    def __init__(
        self,
        payments: PaymentsRepo,
        recon: ReconRepo,
        files: SettlementRepo,
        clock: Clock,
        directory: Path,
    ) -> None:
        self._payments = payments
        self._recon = recon
        self._files = files
        self._clock = clock
        self._dir = directory

    def run(self, business_date: str) -> SettlementFile | None:
        """Write the primary file, or a follow-up of late entries; None if nothing new."""
        start, end = ist_day_bounds_utc(business_date)
        payments = self._payments.list_completed_between(iso_z(start), iso_z(end))
        existing = self._files.list_by_date(business_date)
        if existing:
            seen = {pid for f in existing for pid in _payment_ids(Path(f.path))}
            payments = [p for p in payments if p.id not in seen]
            if not payments:
                return None
        sequence = existing[-1].sequence + 1 if existing else 0
        kind = SettlementKind.FOLLOWUP if existing else SettlementKind.PRIMARY
        name = (
            f"{business_date}-primary.csv"
            if not existing
            else (f"{business_date}-followup-{sequence}.csv")
        )
        rows = "".join(self._row(p) for p in payments)
        checksum = hashlib.sha256(rows.encode()).hexdigest()
        text = f"{HEADER}{rows}# row_count={len(payments)}\n# sha256={checksum}\n"
        path = self._dir / name
        _write_once(path, text)
        record = SettlementFile(
            id=new_settlement_id(),
            business_date=business_date,
            kind=kind,
            sequence=sequence,
            path=str(path),
            row_count=len(payments),
            checksum=checksum,
            written_at=iso_z(self._clock.now()),
        )
        self._files.insert(record)
        return record

    def _row(self, p: Payment) -> str:
        status = self._recon.status_for_payment(p.id) or ReconStatus.UNMATCHED_INTERNAL
        flag = "false" if status is ReconStatus.MATCHED else "true"
        ref = p.rail_reference or ""
        return f"{p.id},{p.rail.value},{p.amount_paise},{ref},{status.value},{flag}\n"


def _payment_ids(path: Path) -> list[str]:
    lines = path.read_text().splitlines()[1:]
    return [ln.split(",")[0] for ln in lines if not ln.startswith("#")]


def _write_once(path: Path, text: str) -> None:
    """Write via temp file and hard link so an existing target is never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    finally:
        tmp.unlink()
    path.chmod(0o444)
