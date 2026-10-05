import dataclasses

import pytest

from paybridge.types import models
from paybridge.types.enums import PaymentState, Rail
from paybridge.types.models import Payment


def test_payment_is_frozen_with_int_paise() -> None:
    payment = Payment(
        id="pay_1",
        customer_id="cus_001",
        idempotency_key="k",
        request_hash="h",
        amount_paise=100,
        rail=Rail.UPI,
        beneficiary="B",
        state=PaymentState.CREATED,
        created_at="t",
        updated_at="t",
    )
    assert payment.reason_code is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        payment.amount_paise = 5  # type: ignore[misc]


def test_paise_fields_are_never_float() -> None:
    for obj in vars(models).values():
        if dataclasses.is_dataclass(obj):
            for field in dataclasses.fields(obj):
                if "paise" in field.name:
                    assert "float" not in str(field.type)


def test_permanent_rail_error_carries_reason_code() -> None:
    from paybridge.types.errors import PermanentRailError

    error = PermanentRailError("rejected", "INSUFFICIENT_FUNDS")
    assert (error.code, error.reason_code) == ("PERMANENT_RAIL_ERROR", "INSUFFICIENT_FUNDS")
