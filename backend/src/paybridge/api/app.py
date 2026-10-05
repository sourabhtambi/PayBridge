"""Application factory."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paybridge.api.container import Container, build_container
from paybridge.api.errors import install_error_handlers
from paybridge.api.routes import (
    customers,
    dashboard,
    health,
    ops,
    payments,
    reconciliation,
    refunds,
    settlement,
    simulation,
)
from paybridge.config.logging_setup import install_masking
from paybridge.config.settings import Settings
from paybridge.repository.migrate import initialize_database
from paybridge.repository.seed import seed_customers
from paybridge.service.outbox_worker import OutboxWorker
from paybridge.service.payment_service import load_known_beneficiaries
from paybridge.service.rail_adapters import build_adapters
from paybridge.service.settlement_scheduler import SettlementScheduler
from paybridge.service.simulation import SimulationStore
from paybridge.types.ports import Clock

log = logging.getLogger(__name__)


async def _schedule(container: Container) -> None:
    scheduler = SettlementScheduler(
        container.clock, lambda day: settlement.run_settlement(container, day)
    )
    while True:
        try:
            scheduler.tick()
        except Exception:
            log.exception("scheduled settlement run failed")
        await asyncio.sleep(container.settings.poll_interval_seconds)


def _startup(container: Container) -> None:
    container.settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    initialize_database(container.db)
    with container.db.write() as conn:
        seed_customers(conn, container.clock)
    load_known_beneficiaries(container.db)


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    install_masking()
    settings = settings or Settings.from_env()
    container = build_container(settings, clock)
    sim = SimulationStore()
    adapters = build_adapters(container.clock, sim)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        _startup(container)
        worker = OutboxWorker(container.db, container.clock, adapters)
        tasks = [asyncio.create_task(worker.run()), asyncio.create_task(_schedule(container))]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="PayBridge", lifespan=lifespan)
    app.state.container = container
    app.state.simulation = sim
    app.state.adapters = adapters
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["X-Role", "X-Customer-Id", "Idempotency-Key", "Content-Type"],
        expose_headers=["Idempotent-Replay"],
    )
    install_error_handlers(app)
    for module in (
        health,
        customers,
        simulation,
        payments,
        ops,
        refunds,
        reconciliation,
        settlement,
        dashboard,
    ):
        app.include_router(module.router)
    return app
