"""Allowed state transitions for payments and refunds."""

from paybridge.types.enums import PaymentState, RefundState
from paybridge.types.errors import InvalidPaymentStateException

PAYMENT_TRANSITIONS: dict[PaymentState, frozenset[PaymentState]] = {
    PaymentState.CREATED: frozenset({PaymentState.SUBMITTED}),
    PaymentState.SUBMITTED: frozenset({PaymentState.COMPLETED, PaymentState.FAILED}),
    PaymentState.COMPLETED: frozenset({PaymentState.REFUNDED}),
    PaymentState.FAILED: frozenset(),
    PaymentState.REFUNDED: frozenset(),
}

REFUND_TRANSITIONS: dict[RefundState, frozenset[RefundState]] = {
    RefundState.REQUESTED: frozenset({RefundState.APPROVED, RefundState.REJECTED}),
    RefundState.APPROVED: frozenset({RefundState.EXECUTED, RefundState.FAILED}),
    RefundState.EXECUTED: frozenset(),
    RefundState.REJECTED: frozenset(),
    RefundState.FAILED: frozenset(),
}


def is_valid_payment_transition(src: PaymentState, dst: PaymentState) -> bool:
    return dst in PAYMENT_TRANSITIONS[src]


def is_valid_refund_transition(src: RefundState, dst: RefundState) -> bool:
    return dst in REFUND_TRANSITIONS[src]


def assert_payment_transition(src: PaymentState, dst: PaymentState) -> None:
    if not is_valid_payment_transition(src, dst):
        raise InvalidPaymentStateException(f"Payment cannot move from {src} to {dst}")


def assert_refund_transition(src: RefundState, dst: RefundState) -> None:
    if not is_valid_refund_transition(src, dst):
        raise InvalidPaymentStateException(f"Refund cannot move from {src} to {dst}")


def is_valid_transition(
    current: PaymentState | RefundState, target: PaymentState | RefundState
) -> bool:
    """Generic dispatcher; entity inferred from state type. False on mismatched types."""
    if isinstance(current, PaymentState) and isinstance(target, PaymentState):
        return is_valid_payment_transition(current, target)
    if isinstance(current, RefundState) and isinstance(target, RefundState):
        return is_valid_refund_transition(current, target)
    return False


def assert_transition(
    current: PaymentState | RefundState, target: PaymentState | RefundState
) -> None:
    """Raise InvalidPaymentStateException unless the transition is allowed."""
    if not is_valid_transition(current, target):
        raise InvalidPaymentStateException(f"Cannot move from {current} to {target}")
