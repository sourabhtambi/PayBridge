"""POST /test/reset, mounted only when PAYBRIDGE_ENV=test."""

from fastapi import APIRouter, Depends, Request

from paybridge.api.container import Container
from paybridge.api.deps import get_container
from paybridge.service.test_reset import reset_state

router = APIRouter()


@router.post("/test/reset")
def reset(request: Request, container: Container = Depends(get_container)) -> dict[str, str]:
    reset_state(
        container.db,
        container.clock,
        container.settings.settlement_dir,
        request.app.state.simulation,
    )
    return {"status": "reset"}
