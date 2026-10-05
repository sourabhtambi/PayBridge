"""Per-rail settings."""

from dataclasses import dataclass

from paybridge.types.enums import Rail, SimulationMode


@dataclass(frozen=True)
class RailSettings:
    reference_prefix: str
    supported_modes: frozenset[SimulationMode]


RAIL_SETTINGS: dict[Rail, RailSettings] = {
    rail: RailSettings(
        reference_prefix=rail.value,
        supported_modes=frozenset(SimulationMode),
    )
    for rail in Rail
}
