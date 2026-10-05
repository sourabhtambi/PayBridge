"""Composition root."""

from dataclasses import dataclass

from paybridge.config.settings import Settings
from paybridge.lib.clock import SystemClock
from paybridge.repository.db import Database
from paybridge.types.ports import Clock


@dataclass(frozen=True)
class Container:
    settings: Settings
    db: Database
    clock: Clock


def build_container(settings: Settings, clock: Clock | None = None) -> Container:
    db = Database(settings.db_path, settings.busy_timeout_ms)
    return Container(settings, db, clock or SystemClock())
