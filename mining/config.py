"""Configuration constants and simulation parameters for the mining domain."""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Time constants (all in minutes)
# ---------------------------------------------------------------------------
HOURS_TO_MINUTES = 60

TRAVEL_TIME_MINUTES = 30  # travel between mine site and unload station

MIN_MINING_HOURS = 1
MAX_MINING_HOURS = 5

MIN_UNLOAD_MINUTES = 30
MAX_UNLOAD_MINUTES = 60


# ---------------------------------------------------------------------------
# Simulation configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SimConfig:
    """Immutable configuration for a simulation run.

    Attributes:
        num_trucks:     Number of mining trucks (n).
        num_stations:   Number of unload stations (m).
        duration_hours: Total simulation time in hours.
        random_seed:    Optional seed for reproducible runs.
    """

    num_trucks: int = 10
    num_stations: int = 3
    duration_hours: int = 72
    random_seed: int | None = None

    def __post_init__(self) -> None:
        for name in ("num_trucks", "num_stations", "duration_hours"):
            value = getattr(self, name)
            if value < 1:
                raise ValueError(f"{name} must be at least 1 (got {value})")

    @property
    def duration_minutes(self) -> float:
        """Simulation duration converted to minutes (the internal time unit)."""
        return float(self.duration_hours * HOURS_TO_MINUTES)
