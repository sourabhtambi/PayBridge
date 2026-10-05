"""GET /customers."""

from fastapi import APIRouter, Depends

from paybridge.api.container import Container
from paybridge.api.deps import get_container
from paybridge.repository.customers_repo import CustomersRepo

router = APIRouter()


@router.get("/customers")
def list_customers(container: Container = Depends(get_container)) -> dict[str, object]:
    with container.db.read() as conn:
        items = [
            {"id": c.id, "name": c.name, "role": c.role.value}
            for c in CustomersRepo(conn).list_all()
        ]
    return {"items": items, "total": len(items)}
