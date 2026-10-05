"""Typed domain errors. Each carries a stable machine-readable code."""


class DomainError(Exception):
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    field: str | None = None

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        if field is not None:
            self.field = field


class AmountBelowMinimum(ValidationError):
    code = "AMOUNT_BELOW_MINIMUM"
    field = "amount_paise"


class InvalidPaymentStateException(DomainError):
    code = "INVALID_TRANSITION"


class IdempotencyConflict(DomainError):
    code = "IDEMPOTENCY_KEY_CONFLICT"


class DuplicateKeyError(DomainError):
    code = "DUPLICATE_KEY"


class NotFound(DomainError):
    code = "NOT_FOUND"


class Forbidden(DomainError):
    code = "FORBIDDEN"


class PaymentNotRefundable(DomainError):
    code = "PAYMENT_NOT_REFUNDABLE"


class RefundAlreadyExists(DomainError):
    code = "REFUND_ALREADY_EXISTS"


class RefundAlreadyDecided(DomainError):
    code = "REFUND_ALREADY_DECIDED"


class ReconAlreadyResolved(DomainError):
    code = "RECON_ALREADY_RESOLVED"


class PermanentRailError(DomainError):
    code = "PERMANENT_RAIL_ERROR"

    def __init__(self, message: str, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class TransientRailError(DomainError):
    code = "TRANSIENT_RAIL_ERROR"


class Unauthenticated(DomainError):
    code = "UNAUTHENTICATED"
