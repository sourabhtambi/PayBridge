"""/settlement endpoints (admin only)."""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Body, Depends, Query, Response
from fastapi.responses import JSONResponse

from paybridge.api.container import Container
from paybridge.api.deps import get_container, require_roles
from paybridge.lib.timeutil import business_date
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.recon_repo import ReconRepo
from paybridge.repository.settlement_repo import SettlementRepo
from paybridge.service.settlement_service import SettlementService
from paybridge.types.enums import Role, SettlementKind
from paybridge.types.errors import NotFound, ValidationError
from paybridge.types.models import SettlementFile

_BODY = Body(default=None)
router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


def _view(f: SettlementFile) -> dict[str, object]:
    return {
        "id": f.id,
        "business_date": f.business_date,
        "kind": f.kind.value,
        "row_count": f.row_count,
        "checksum": f.checksum,
        "written_at": f.written_at,
    }


def run_settlement(container: Container, day: str) -> SettlementFile | None:
    with container.db.write() as conn:
        service = SettlementService(
            PaymentsRepo(conn),
            ReconRepo(conn),
            SettlementRepo(conn),
            container.clock,
            container.settings.settlement_dir,
        )
        return service.run(day)


def _parse_day(body: dict[str, object] | None, today: str) -> str:
    raw = body.get("business_date") if body else None
    if raw is None:
        return today
    try:
        if not isinstance(raw, str) or len(raw) != 10:
            raise ValueError
        day = date.fromisoformat(raw).isoformat()
    except ValueError:
        raise ValidationError("business_date must be YYYY-MM-DD", "business_date") from None
    if day > today:
        raise ValidationError("business_date is in the future", "business_date")
    return day


@router.post("/settlement/run")
def run(
    body: dict[str, object] | None = _BODY,
    container: Container = Depends(get_container),
) -> JSONResponse:
    day = _parse_day(body, business_date(container.clock.now()))
    record = run_settlement(container, day)
    if record is None:
        return JSONResponse({"file": None, "message": f"Primary file for {day} already exists"})
    status = 201 if record.kind is SettlementKind.PRIMARY else 200
    return JSONResponse({"file": _view(record), "message": f"{record.kind.value} written"}, status)


@router.get("/settlement/files")
def list_files(
    business_date: str | None = Query(default=None),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    with container.db.read() as conn:
        repo = SettlementRepo(conn)
        files = repo.list_by_date(business_date) if business_date else repo.list_all()
    items = [_view(f) for f in files][:500]
    return {"items": items, "total": len(items)}


@router.get("/settlement/files/{file_id}")
def download(file_id: str, container: Container = Depends(get_container)) -> Response:
    with container.db.read() as conn:
        record = SettlementRepo(conn).get(file_id)
    if record is None:
        raise NotFound("Settlement file not found")
    name = f"{record.business_date}-{record.kind.value}.csv"
    return Response(
        Path(record.path).read_text(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )
