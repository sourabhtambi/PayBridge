import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from paybridge.repository.db import Database
from paybridge.repository.migrate import initialize_database
from paybridge.repository.seed import seed_customers
from tests.support.fake_clock import FakeClock


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    initialize_database(db)
    return db


@pytest.fixture
def conn(database: Database, clock: FakeClock) -> Iterator[sqlite3.Connection]:
    connection = database.connect()
    seed_customers(connection, clock)
    yield connection
    connection.close()
