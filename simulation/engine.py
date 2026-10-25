"""Backward-compatibility adapter for SimulationEngine.

Wraps :class:`sim_engine.SimulationEngine` and :class:`mining.MiningSimulation`
to preserve the original monolithic class interface and logging behavior.
"""

from __future__ import annotations

import logging
from typing import Any

from mining import MiningSimulation, MiningTruck, SimConfig, UnloadStation
from sim_engine import SimulationEngine as CoreEngine

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Legacy simulation engine facade.

    Attributes:
        config:   Simulation configuration parameters.
        clock:    Current simulation time in minutes.
        trucks:   List of all mining trucks.
        stations: List of all unload stations.
    """

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self._core_engine = CoreEngine()
        self._scenario = MiningSimulation(self._core_engine, config, logger=logger)
        self._has_run = False

    @property
    def clock(self) -> float:
        """Current virtual simulation time in minutes."""
        return self._core_engine.clock

    @property
    def seed(self) -> int:
        """Simulation random seed."""
        return self._scenario.seed

    @property
    def rng(self) -> Any:
        """Domain random number generator."""
        return self._scenario.rng

    @rng.setter
    def rng(self, value: Any) -> None:
        self._scenario.rng = value

    @property
    def trucks(self) -> list[MiningTruck]:
        """List of mining trucks."""
        return self._scenario.trucks

    @property
    def stations(self) -> list[UnloadStation]:
        """List of unload stations."""
        return self._scenario.stations

    @property
    def event_queue(self) -> list[Any]:
        """Priority queue of scheduled events."""
        return self._core_engine._queue

    def run(self) -> None:
        """Execute the simulation to completion."""
        if self._has_run:
            raise RuntimeError(
                "SimulationEngine.run() can only be called once; "
                "create a new engine for another run."
            )
        self._has_run = True

        config = self.config
        logger.info(
            "Starting simulation: %d trucks, %d stations, %d h (seed=%s)",
            config.num_trucks,
            config.num_stations,
            config.duration_hours,
            config.random_seed,
        )

        self._scenario.setup()
        self._core_engine.run(until=config.duration_minutes)

        logger.debug(
            "%d events scheduled after t=%.0f were not processed",
            len(self._core_engine._queue),
            config.duration_minutes,
        )
        self._scenario.finalize(until=config.duration_minutes)

        logger.info(
            "Simulation finished at t=%.0f min: %d events processed, %d loads delivered",
            self.clock,
            self._core_engine.events_processed,
            sum(t.loads_delivered for t in self.trucks),
        )


__all__ = ["SimulationEngine"]
