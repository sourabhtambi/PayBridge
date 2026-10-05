"""Shared domain enumerations. Values match the stored strings."""

from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "customer"
    OPS = "ops"
    ADMIN = "admin"


class Rail(StrEnum):
    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"


class PaymentState(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class RefundState(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ReconStatus(StrEnum):
    MATCHED = "matched"
    UNMATCHED_INTERNAL = "unmatched_internal"
    UNMATCHED_EXTERNAL = "unmatched_external"
    AMOUNT_MISMATCH = "amount_mismatch"


class AttemptOutcome(StrEnum):
    SUCCESS = "success"
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class OutboxStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SENT = "SENT"


class SettlementKind(StrEnum):
    PRIMARY = "primary"
    FOLLOWUP = "followup"


class SimulationMode(StrEnum):
    SUCCESS = "success"
    PERMANENT_FAILURE = "permanent_failure"
    TRANSIENT = "transient"


class EventType(StrEnum):
    PAYMENT_CREATED = "PAYMENT_CREATED"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_RETRY_SCHEDULED = "PAYMENT_RETRY_SCHEDULED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_FLAGGED_STUCK = "PAYMENT_FLAGGED_STUCK"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUND_APPROVED = "REFUND_APPROVED"
    REFUND_REJECTED = "REFUND_REJECTED"
    REFUND_EXECUTED = "REFUND_EXECUTED"
    REFUND_FAILED = "REFUND_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"


class ReasonCode(StrEnum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_BENEFICIARY = "INVALID_BENEFICIARY"
    BENEFICIARY_ACCOUNT_CLOSED = "BENEFICIARY_ACCOUNT_CLOSED"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    RETRIES_EXHAUSTED = "RETRIES_EXHAUSTED"
    REJECTED_BY_ADMIN = "REJECTED_BY_ADMIN"
