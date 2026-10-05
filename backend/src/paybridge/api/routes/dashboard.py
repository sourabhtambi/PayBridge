"""/dashboard/summary (admin only)."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from paybridge.api.container import Container
from paybridge.api.deps import get_container, require_roles
from paybridge.api.routes.refunds import _view as refund_view
from paybridge.api.routes.settlement import _view as file_view
from paybridge.lib.timeutil import business_date, iso_z, ist_day_bounds_utc
from paybridge.repository.payments_repo import PaymentsRepo
from paybridge.repository.refunds_repo import RefundsRepo
from paybridge.repository.settlement_repo import SettlementRepo
from paybridge.types.enums import PaymentState, Rail, RefundState, Role
from paybridge.types.errors import ValidationError

router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


def _parse_day(raw: str | None, today: str) -> str:
    if raw is None:
        return today
    try:
        if len(raw) != 10:
            raise ValueError
        day = date.fromisoformat(raw).isoformat()
    except ValueError:
        raise ValidationError("date must be YYYY-MM-DD", "date") from None
    if day > today:
        raise ValidationError("date is in the future", "date")
    return day


@router.get("/dashboard/summary")
def summary(
    date: str | None = Query(default=None),
    container: Container = Depends(get_container),
) -> dict[str, object]:
    day = _parse_day(date, business_date(container.clock.now()))
    start, end = (iso_z(b) for b in ist_day_bounds_utc(day))
    with container.db.read() as conn:
        payments = PaymentsRepo(conn)
        totals = payments.rail_totals(start, end)
        counts = payments.state_counts(start, end)
        refunds = RefundsRepo(conn).list_by_state(RefundState.REQUESTED)
        files = SettlementRepo(conn).list_by_date(day)
    return {
        "date": day,
        "rails": [
            {
                "rail": r.value,
                "payment_count": totals.get(r, (0, 0))[0],
                "total_paise": totals.get(r, (0, 0))[1],
            }
            for r in Rail
        ],
        "status_counts": {s.value: counts.get(s, 0) for s in PaymentState},
        "pending_refunds": [refund_view(r) for r in refunds],
        "settlement_files": [file_view(f) for f in files],
    }
