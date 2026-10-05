"""Test-only: return the app to a freshly seeded state (payments, files, simulation)."""

import shutil
from pathlib import Path

from paybridge.repository.db import Database
from paybridge.repository.migrate import initialize_database
from paybridge.repository.reset import wipe_database
from paybridge.repository.seed import seed_customers
from paybridge.service.simulation import SimulationStore
from paybridge.types.ports import Clock


def reset_state(db: Database, clock: Clock, settlement_dir: Path, sim: SimulationStore) -> None:
    wipe_database(db)
    initialize_database(db)  # recreates the dropped append-only triggers
    with db.write() as conn:
        seed_customers(conn, clock)
    shutil.rmtree(settlement_dir, ignore_errors=True)
    sim.reset()
