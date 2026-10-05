"""Exception handlers producing the error envelope."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from paybridge.types.errors import (
    DomainError,
    Forbidden,
    IdempotencyConflict,
    NotFound,
    PaymentNotRefundable,
    ReconAlreadyResolved,
    RefundAlreadyDecided,
    RefundAlreadyExists,
    Unauthenticated,
    ValidationError,
)

_STATUS: dict[type[DomainError], int] = {
    Unauthenticated: 401,
    Forbidden: 403,
    NotFound: 404,
    IdempotencyConflict: 409,
    RefundAlreadyExists: 409,
    RefundAlreadyDecided: 409,
    ReconAlreadyResolved: 409,
}
log = logging.getLogger(__name__)


def _envelope(status: int, code: str, message: str, field: str | None = None) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if status == 422:
        error["fields"] = [{"field": field, "message": message}] if field else []
    return JSONResponse({"error": error}, status_code=status)


async def _domain(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    if isinstance(exc, ValidationError):
        return _envelope(422, exc.code, exc.message, exc.field)
    if isinstance(exc, PaymentNotRefundable):
        return _envelope(422, exc.code, exc.message)
    return _envelope(_STATUS.get(type(exc), 500), exc.code, exc.message)


async def _request_invalid(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    first = exc.errors()[0]
    field = str(first["loc"][-1])
    return _envelope(422, "VALIDATION_ERROR", str(first["msg"]), field)


async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error", exc_info=exc)
    return _envelope(500, "INTERNAL_ERROR", "Unexpected error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain)
    app.add_exception_handler(RequestValidationError, _request_invalid)
    app.add_exception_handler(Exception, _unexpected)
