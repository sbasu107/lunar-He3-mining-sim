"""Backward-compatibility facade for mining configuration."""

from mining.config import (
    HOURS_TO_MINUTES,
    MAX_MINING_HOURS,
    MAX_UNLOAD_MINUTES,
    MIN_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    TRAVEL_TIME_MINUTES,
    SimConfig,
)

__all__ = [
    "HOURS_TO_MINUTES",
    "MAX_MINING_HOURS",
    "MAX_UNLOAD_MINUTES",
    "MIN_MINING_HOURS",
    "MIN_UNLOAD_MINUTES",
    "TRAVEL_TIME_MINUTES",
    "SimConfig",
]
