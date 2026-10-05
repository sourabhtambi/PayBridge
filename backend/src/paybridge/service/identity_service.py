"""Resolve the caller from demo role headers."""

from dataclasses import dataclass

from paybridge.repository.customers_repo import CustomersRepo
from paybridge.types.enums import Role
from paybridge.types.errors import Unauthenticated


@dataclass(frozen=True)
class Caller:
    role: Role
    customer_id: str | None


def resolve_caller(role: str | None, customer_id: str | None, repo: CustomersRepo) -> Caller:
    try:
        parsed = Role(role) if role else None
    except ValueError:
        parsed = None
    if parsed is None:
        raise Unauthenticated("Missing or unknown X-Role")
    if parsed is not Role.CUSTOMER:
        return Caller(parsed, None)
    customer = repo.get(customer_id) if customer_id else None
    if customer is None or customer.role is not Role.CUSTOMER:
        raise Unauthenticated("Missing or invalid X-Customer-Id")
    return Caller(parsed, customer.id)
