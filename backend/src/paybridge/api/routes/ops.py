"""/ops/stuck-payments (ops, admin)."""

from fastapi import APIRouter, Depends

from paybridge.api.container import Container
from paybridge.api.deps import get_container, require_roles
from paybridge.service.stuck_service import detect_and_list
from paybridge.types.enums import Role

router = APIRouter(dependencies=[Depends(require_roles(Role.OPS, Role.ADMIN))])


@router.get("/ops/stuck-payments")
def stuck_payments(container: Container = Depends(get_container)) -> dict[str, object]:
    items = detect_and_list(container.db, container.clock)
    return {"items": items, "total": len(items)}
