"""Request dependencies: container access, caller resolution, role guards."""

from collections.abc import Callable

from fastapi import Depends, Header, Request

from paybridge.api.container import Container
from paybridge.repository.customers_repo import CustomersRepo
from paybridge.service.identity_service import Caller, resolve_caller
from paybridge.types.enums import Role
from paybridge.types.errors import Forbidden


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_caller(
    container: Container = Depends(get_container),
    x_role: str | None = Header(default=None),
    x_customer_id: str | None = Header(default=None),
) -> Caller:
    with container.db.read() as conn:
        return resolve_caller(x_role, x_customer_id, CustomersRepo(conn))


def require_roles(*roles: Role) -> Callable[[Caller], Caller]:
    def guard(caller: Caller = Depends(get_caller)) -> Caller:
        if caller.role not in roles:
            raise Forbidden("Role not permitted")
        return caller

    return guard
