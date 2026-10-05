"""In-memory mock rail simulation config (resets on restart)."""

import random
from dataclasses import dataclass

from paybridge.types.enums import Rail, ReasonCode, SimulationMode
from paybridge.types.errors import PermanentRailError, TransientRailError, ValidationError


@dataclass(frozen=True)
class SimulationConfig:
    rail: Rail
    mode: SimulationMode = SimulationMode.SUCCESS
    reason_code: str | None = None
    transient_failure_rate: float = 0.0


class SimulationStore:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._configs = {rail: SimulationConfig(rail) for rail in Rail}

    def all(self) -> list[SimulationConfig]:
        return [self._configs[rail] for rail in Rail]

    def get(self, rail: Rail) -> SimulationConfig:
        return self._configs[rail]

    def set(
        self, rail: Rail, mode: SimulationMode, reason_code: str | None, rate: float | None
    ) -> SimulationConfig:
        if mode is SimulationMode.PERMANENT_FAILURE:
            if reason_code not in {c.value for c in ReasonCode}:
                raise ValidationError("Valid reason_code required", "reason_code")
        elif mode is SimulationMode.TRANSIENT:
            if rate is None:
                raise ValidationError("transient_failure_rate required", "transient_failure_rate")
        config = SimulationConfig(
            rail,
            mode,
            reason_code if mode is SimulationMode.PERMANENT_FAILURE else None,
            rate if mode is SimulationMode.TRANSIENT and rate is not None else 0.0,
        )
        self._configs[rail] = config
        return config

    def check(self, rail: Rail) -> None:
        """Raise the configured failure for this rail, if any."""
        config = self._configs[rail]
        if config.mode is SimulationMode.PERMANENT_FAILURE:
            raise PermanentRailError("Simulated permanent failure", config.reason_code or "")
        if config.mode is SimulationMode.TRANSIENT:
            if self._rng.random() < config.transient_failure_rate:
                raise TransientRailError("Simulated transient failure")
