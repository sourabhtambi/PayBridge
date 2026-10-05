from dataclasses import replace

from paybridge.types.enums import PaymentState, Rail, RefundState
from paybridge.types.models import Payment, Refund

TS = "2026-10-04T09:30:00Z"


def make_payment(**overrides: object) -> Payment:
    base = Payment(
        id="pay_000000000001",
        customer_id="cus_001",
        idempotency_key="key-1",
        request_hash="h" * 64,
        amount_paise=10000,
        rail=Rail.UPI,
        beneficiary="Ravi Kumar",
        state=PaymentState.CREATED,
        created_at=TS,
        updated_at=TS,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def make_refund(**overrides: object) -> Refund:
    base = Refund(
        id="rfd_000000000001",
        payment_id="pay_000000000001",
        amount_paise=10000,
        state=RefundState.REQUESTED,
        requested_by="cus_001",
        created_at=TS,
        updated_at=TS,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]
