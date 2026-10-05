"""POST/GET /refunds."""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from paybridge.api.container import Container
from paybridge.api.deps import get_caller, get_container, require_roles
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.service.identity_service import Caller
from paybridge.service.refund_service import RefundService
from paybridge.types.enums import RefundState, Role
from paybridge.types.errors import ValidationError
from paybridge.types.models import Refund

router = APIRouter()
LIST_CAP = 500
_customer_only = require_roles(Role.CUSTOMER)
_admin_only = require_roles(Role.ADMIN)
ADMIN_ID = "adm_001"


class CreateRefundRequest(BaseModel):
    payment_id: str


def _view(r: Refund) -> dict[str, object]:
    return {
        "id": r.id,
        "payment_id": r.payment_id,
        "amount_paise": r.amount_paise,
        "state": r.state.value,
        "requested_by": r.requested_by,
        "decided_by": r.decided_by,
        "reason_code": r.reason_code,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


@router.post("/refunds", status_code=201)
def create_refund(
    body: CreateRefundRequest,
    caller: Caller = Depends(_customer_only),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    assert caller.customer_id is not None
    refund = RefundService(container.db, container.clock).request_refund(
        caller.customer_id, body.payment_id
    )
    return _view(refund)


@router.get("/refunds")
def list_refunds(
    state: str | None = Query(default=None),
    caller: Caller = Depends(get_caller),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    try:
        parsed = RefundState(state) if state else None
    except ValueError:
        raise ValidationError("Invalid state", "state") from None
    owner = caller.customer_id if caller.role is Role.CUSTOMER else None
    with container.db.read() as conn:
        items = [_view(r) for r in RefundsRepo(conn).list_filtered(owner, parsed, LIST_CAP)]
    return {"items": items, "total": len(items)}


@router.post("/refunds/{refund_id}/approve")
async def approve_refund(
    refund_id: str,
    request: Request,
    _: Caller = Depends(_admin_only),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    service = RefundService(container.db, container.clock, request.app.state.adapters)
    return _view(await service.approve(refund_id, ADMIN_ID))


@router.post("/refunds/{refund_id}/reject")
def reject_refund(
    refund_id: str,
    _: Caller = Depends(_admin_only),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    return _view(RefundService(container.db, container.clock).reject(refund_id, ADMIN_ID))
