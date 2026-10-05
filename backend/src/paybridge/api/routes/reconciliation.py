"""/reconciliation endpoints (ops, admin)."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator

from paybridge.api.container import Container
from paybridge.api.deps import get_container, require_roles
from paybridge.lib.timeutil import business_date, iso_z
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.statements_repo import StatementsRepo
from paybridge.service.identity_service import Caller
from paybridge.service.reconciliation_service import ReconciliationService
from paybridge.service.statement_service import StatementService
from paybridge.types.enums import Rail, ReconStatus, Role
from paybridge.types.errors import NotFound, ReconAlreadyResolved, ValidationError
from paybridge.types.models import ReconciliationResult

_guard = require_roles(Role.OPS, Role.ADMIN)
router = APIRouter(dependencies=[Depends(_guard)])
_ACTOR = {Role.OPS: "ops_001", Role.ADMIN: "adm_001"}
MAX_NOTE = 500


def _parse_date(text: str) -> str:
    try:
        if len(text) != 10:
            raise ValueError
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValidationError("statement_date must be YYYY-MM-DD", "statement_date") from None


class RunRequest(BaseModel):
    statement_date: str

    @field_validator("statement_date")
    @classmethod
    def _valid(cls, v: str) -> str:
        return _parse_date(v)


class ResolveRequest(BaseModel):
    note: str


def _view(r: ReconciliationResult) -> dict[str, object]:
    return {
        "id": r.id,
        "statement_date": r.statement_date,
        "rail": r.rail.value,
        "status": r.status.value,
        "payment_id": r.payment_id,
        "statement_entry_id": r.statement_entry_id,
        "payment_ref": r.payment_ref,
        "payment_amount_paise": r.payment_amount_paise,
        "statement_amount_paise": r.statement_amount_paise,
        "resolved": r.resolved,
        "resolution_note": r.resolution_note,
        "resolved_by": r.resolved_by,
        "resolved_at": r.resolved_at,
    }


@router.post("/reconciliation/run")
def run(body: RunRequest, container: Container = Depends(get_container)) -> dict[str, object]:
    if body.statement_date > business_date(container.clock.now()):
        raise ValidationError("statement_date is in the future", "statement_date")
    with container.db.write() as conn:
        pr, sr, rr = PaymentsRepo(conn), StatementsRepo(conn), ReconRepo(conn)
        StatementService(pr, sr, container.clock).generate(body.statement_date)
        ReconciliationService(pr, sr, rr, container.clock).run(body.statement_date)
        results = rr.list_by_date(body.statement_date)
    counts = {s.value: sum(1 for r in results if r.status is s) for s in ReconStatus}
    return {"statement_date": body.statement_date, "counts": counts}


def _enum[E: (Rail, ReconStatus)](cls: type[E], value: str | None, field: str) -> E | None:
    try:
        return cls(value) if value else None
    except ValueError:
        raise ValidationError(f"Invalid {field}", field) from None


@router.get("/reconciliation/unmatched")
def unmatched(
    status: str | None = Query(default=None),
    rail: str | None = Query(default=None),
    statement_date: str | None = Query(default=None),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    st = _enum(ReconStatus, status, "status")
    rl = _enum(Rail, rail, "rail")
    day = _parse_date(statement_date) if statement_date else None
    with container.db.read() as conn:
        rows = ReconRepo(conn).list_unresolved()
    items = [
        _view(r)
        for r in rows
        if (st is None or r.status is st)
        and (rl is None or r.rail is rl)
        and (day is None or r.statement_date == day)
    ]
    return {"items": items, "total": len(items)}


@router.post("/reconciliation/{result_id}/resolve")
def resolve(
    result_id: str,
    body: ResolveRequest,
    caller: Caller = Depends(_guard),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    note = body.note.strip()
    if not note or len(note) > MAX_NOTE:
        raise ValidationError("note must be 1-500 characters", "note")
    now = iso_z(container.clock.now())
    with container.db.write() as conn:
        repo = ReconRepo(conn)
        current = repo.get(result_id)
        if current is None:
            raise NotFound("Reconciliation result not found")
        if current.status is ReconStatus.MATCHED:
            raise ValidationError("Matched results cannot be resolved", "id")
        if current.resolved or not repo.resolve(result_id, note, _ACTOR[caller.role], now):
            raise ReconAlreadyResolved("Result already resolved")
        updated = repo.get(result_id)
    assert updated is not None
    return _view(updated)
