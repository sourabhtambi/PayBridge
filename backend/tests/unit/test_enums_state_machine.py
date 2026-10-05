import pytest

from paybridge.types.enums import PaymentState, ReconStatus, RefundState, Role
from paybridge.types.errors import InvalidPaymentStateException
from paybridge.types.state_machine import (
    assert_payment_transition,
    assert_refund_transition,
    assert_transition,
    is_valid_payment_transition,
    is_valid_refund_transition,
    is_valid_transition,
)


def test_enum_values_match_brd() -> None:
    assert {m.value for m in PaymentState} == {
        "CREATED",
        "SUBMITTED",
        "COMPLETED",
        "FAILED",
        "REFUNDED",
    }
    assert {m.value for m in RefundState} == {
        "REQUESTED",
        "APPROVED",
        "EXECUTED",
        "REJECTED",
        "FAILED",
    }
    assert {m.value for m in ReconStatus} == {
        "matched",
        "unmatched_internal",
        "unmatched_external",
        "amount_mismatch",
    }
    assert {m.value for m in Role} == {"customer", "ops", "admin"}


@pytest.mark.parametrize(
    ("src", "dst"),
    [
        (PaymentState.CREATED, PaymentState.SUBMITTED),
        (PaymentState.SUBMITTED, PaymentState.COMPLETED),
        (PaymentState.SUBMITTED, PaymentState.FAILED),
    ],
)
# AC-04
def test_valid_payment_transitions(src: PaymentState, dst: PaymentState) -> None:
    assert is_valid_payment_transition(src, dst) is True
    assert_payment_transition(src, dst)


@pytest.mark.parametrize(
    ("src", "dst"),
    [
        (PaymentState.COMPLETED, PaymentState.SUBMITTED),
        (PaymentState.FAILED, PaymentState.COMPLETED),
        (PaymentState.CREATED, PaymentState.COMPLETED),
        (PaymentState.COMPLETED, PaymentState.COMPLETED),
    ],
)
# AC-04
def test_invalid_payment_transitions(src: PaymentState, dst: PaymentState) -> None:
    assert is_valid_payment_transition(src, dst) is False
    with pytest.raises(InvalidPaymentStateException) as exc:
        assert_payment_transition(src, dst)
    assert exc.value.code == "INVALID_TRANSITION"


def test_refund_transitions() -> None:
    assert is_valid_refund_transition(RefundState.REQUESTED, RefundState.APPROVED)
    assert is_valid_refund_transition(RefundState.REQUESTED, RefundState.REJECTED)
    assert is_valid_refund_transition(RefundState.APPROVED, RefundState.EXECUTED)
    assert is_valid_refund_transition(RefundState.APPROVED, RefundState.FAILED)
    assert not is_valid_refund_transition(RefundState.EXECUTED, RefundState.APPROVED)
    assert not is_valid_refund_transition(RefundState.REJECTED, RefundState.APPROVED)
    assert_refund_transition(RefundState.REQUESTED, RefundState.APPROVED)
    with pytest.raises(InvalidPaymentStateException):
        assert_refund_transition(RefundState.REQUESTED, RefundState.EXECUTED)


def test_generic_is_valid_transition_payment() -> None:
    assert is_valid_transition(PaymentState.CREATED, PaymentState.SUBMITTED) is True
    assert is_valid_transition(PaymentState.COMPLETED, PaymentState.SUBMITTED) is False
    assert is_valid_transition(PaymentState.FAILED, PaymentState.COMPLETED) is False


def test_generic_is_valid_transition_refund() -> None:
    assert is_valid_transition(RefundState.REQUESTED, RefundState.APPROVED) is True
    assert is_valid_transition(RefundState.APPROVED, RefundState.FAILED) is True
    assert is_valid_transition(RefundState.FAILED, RefundState.APPROVED) is False
    assert is_valid_transition(RefundState.EXECUTED, RefundState.FAILED) is False


def test_generic_assert_transition() -> None:
    assert_transition(PaymentState.SUBMITTED, PaymentState.COMPLETED)
    assert_transition(RefundState.APPROVED, RefundState.EXECUTED)
    with pytest.raises(InvalidPaymentStateException) as exc:
        assert_transition(PaymentState.COMPLETED, PaymentState.SUBMITTED)
    assert exc.value.code == "INVALID_TRANSITION"
    with pytest.raises(InvalidPaymentStateException):
        assert_transition(RefundState.REJECTED, RefundState.APPROVED)


def test_generic_transition_mismatched_state_types() -> None:
    assert is_valid_transition(PaymentState.CREATED, RefundState.APPROVED) is False
    with pytest.raises(InvalidPaymentStateException):
        assert_transition(RefundState.REQUESTED, PaymentState.SUBMITTED)
