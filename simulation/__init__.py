"""Lunar Helium-3 Mining Simulation package (backward-compatibility facade)."""

import logging

from .config import SimConfig
from .engine import SimulationEngine
from .models import Event, EventType, MiningTruck, TruckState, UnloadStation
from .reporting import Reporter

# Library code never configures output; applications (e.g. main.py) decide
# where log records go and at what level.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "Event",
    "EventType",
    "MiningTruck",
    "Reporter",
    "SimConfig",
    "SimulationEngine",
    "TruckState",
    "UnloadStation",
]
