"""/admin/simulation (admin only)."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from paybridge.api.deps import require_roles
from paybridge.service.simulation import SimulationConfig, SimulationStore
from paybridge.types.enums import Rail, Role, SimulationMode
from paybridge.types.errors import NotFound

router = APIRouter(dependencies=[Depends(require_roles(Role.ADMIN))])


class SimulationUpdate(BaseModel):
    mode: SimulationMode
    reason_code: str | None = None
    transient_failure_rate: float | None = Field(default=None, ge=0, le=1)


def _dump(c: SimulationConfig) -> dict[str, object]:
    return {
        "rail": c.rail.value,
        "mode": c.mode.value,
        "reason_code": c.reason_code,
        "transient_failure_rate": c.transient_failure_rate,
    }


def _store(request: Request) -> SimulationStore:
    store: SimulationStore = request.app.state.simulation
    return store


@router.get("/admin/simulation")
def get_simulation(request: Request) -> dict[str, object]:
    items = [_dump(c) for c in _store(request).all()]
    return {"items": items, "total": len(items)}


@router.put("/admin/simulation/{rail}")
def put_simulation(rail: str, body: SimulationUpdate, request: Request) -> dict[str, object]:
    try:
        rail_enum = Rail(rail)
    except ValueError:
        raise NotFound("Unknown rail") from None
    config = _store(request).set(
        rail_enum, body.mode, body.reason_code, body.transient_failure_rate
    )
    return _dump(config)
