"""POST/GET /payments."""

import json

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, StrictInt

from paybridge.api.container import Container
from paybridge.api.deps import get_caller, get_container, require_roles
from paybridge.repository.attempts_repo import AttemptsRepo
from paybridge.repository.events_repo import EventsRepo
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.service.identity_service import Caller
from paybridge.service.payment_service import PaymentService
from paybridge.types.enums import PaymentState, Role
from paybridge.types.errors import NotFound, ValidationError
from paybridge.types.models import Payment

router = APIRouter()
LIST_CAP = 500
MAX_KEY_LENGTH = 128
_customer_only = require_roles(Role.CUSTOMER)


class CreatePaymentRequest(BaseModel):
    amount_paise: StrictInt
    beneficiary: str


def _view(p: Payment, refunds: RefundsRepo) -> dict[str, object]:
    r = refunds.get_for_payment(p.id)
    return {
        "id": p.id,
        "customer_id": p.customer_id,
        "amount_paise": p.amount_paise,
        "rail": p.rail.value,
        "beneficiary": p.beneficiary,
        "state": p.state.value,
        "reason_code": p.reason_code,
        "rail_reference": p.rail_reference,
        "refund": {"id": r.id, "state": r.state.value, "reason_code": r.reason_code} if r else None,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.post("/payments", status_code=202)
def create_payment(
    body: CreatePaymentRequest,
    response: Response,
    caller: Caller = Depends(_customer_only),
    container: Container = Depends(get_container),
    idempotency_key: str | None = Header(default=None),
) -> dict[str, object]:
    if not idempotency_key or len(idempotency_key) > MAX_KEY_LENGTH:
        raise ValidationError("Idempotency-Key must be 1-128 characters", "Idempotency-Key")
    assert caller.customer_id is not None
    result = PaymentService(container.db, container.clock).create_payment(
        caller.customer_id, idempotency_key, body.amount_paise, body.beneficiary
    )
    if result.replay:
        response.status_code = 200
        response.headers["Idempotent-Replay"] = "true"
    with container.db.read() as conn:
        return _view(result.payment, RefundsRepo(conn))


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    caller: Caller = Depends(get_caller),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    with container.db.read() as conn:
        p = PaymentsRepo(conn).get(payment_id)
        if p is None or (caller.role is Role.CUSTOMER and p.customer_id != caller.customer_id):
            raise NotFound("Payment not found")
        events = [
            {"id": e.id, "type": e.type.value, "payload": json.loads(e.payload), "at": e.at}
            for e in EventsRepo(conn).list_for_payment(p.id)
        ]
        attempts = [
            {
                "attempt_no": a.attempt_no,
                "outcome": a.outcome.value,
                "error_code": a.error_code,
                "at": a.at,
            }
            for a in AttemptsRepo(conn).list_for_payment(p.id)
        ]
        return {**_view(p, RefundsRepo(conn)), "events": events, "attempts": attempts}


@router.get("/payments")
def list_payments(
    state: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    caller: Caller = Depends(get_caller),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    try:
        parsed = PaymentState(state) if state else None
    except ValueError:
        raise ValidationError("Invalid state", "state") from None
    owner = caller.customer_id if caller.role is Role.CUSTOMER else customer_id
    with container.db.read() as conn:
        refunds = RefundsRepo(conn)
        items = [
            _view(p, refunds) for p in PaymentsRepo(conn).list_filtered(owner, parsed, LIST_CAP)
        ]
    return {"items": items, "total": len(items)}
