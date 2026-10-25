"""Mining domain scenario coordinator.

Orchestrates the lunar He-3 mining simulation by wiring domain entities
(trucks, stations) with the domain-agnostic :class:`sim_engine.SimulationEngine`.
"""

from __future__ import annotations

import functools
import logging
import random

from sim_engine import SimulationEngine

from .config import (
    HOURS_TO_MINUTES,
    MAX_MINING_HOURS,
    MAX_UNLOAD_MINUTES,
    MIN_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    TRAVEL_TIME_MINUTES,
    SimConfig,
)
from .models import MiningTruck, TruckState, UnloadStation

logger = logging.getLogger(__name__)

# The MiningTruck attribute that accumulates time spent in each state.
_STATE_TOTALS = {
    TruckState.MINING: "time_mining",
    TruckState.TRAVELING: "time_traveling",
    TruckState.WAITING: "time_waiting",
    TruckState.UNLOADING: "time_unloading",
}


class MiningSimulation:
    """Lunar He-3 mining scenario built on top of :class:`sim_engine.SimulationEngine`.

    Owns all mining entities (trucks and stations), the domain RNG, and the
    event callback handlers. Call :meth:`setup` to seed initial events,
    then ``engine.run(until)``, then :meth:`finalize` to credit in-progress
    activities.

    Attributes:
        engine:   The simulation engine driving the event loop.
        config:   Immutable simulation parameters.
        trucks:   List of all mining trucks.
        stations: List of all unload stations.
        rng:      Domain-owned random number generator.
    """

    def __init__(
        self,
        engine: SimulationEngine,
        config: SimConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self.engine = engine
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # If no seed was supplied, generate one from OS entropy so the run is
        # still fully reproducible if the user wants to repeat it.
        self.seed: int = (
            config.random_seed
            if config.random_seed is not None
            else random.randrange(2**32)
        )
        self.rng: random.Random = random.Random(self.seed)

        self.trucks = [MiningTruck(id=i) for i in range(config.num_trucks)]
        self.stations = [UnloadStation(id=i) for i in range(config.num_stations)]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Schedule the first MINING_COMPLETE event for every truck.

        All trucks start empty at a mining site at t=0. Each truck's
        initial mining duration is drawn randomly from [1, 5] hours.
        """
        for truck in self.trucks:
            duration = (
                self.rng.randint(MIN_MINING_HOURS, MAX_MINING_HOURS)
                * HOURS_TO_MINUTES
            )
            self.logger.debug(
                "Truck %d arrived at mine: will mine for %d min",
                truck.id,
                duration,
            )
            self.engine.schedule(
                float(duration),
                functools.partial(self._on_mining_complete, truck.id),
                label=f"MINING_COMPLETE truck={truck.id}",
            )

    def finalize(self, until: float) -> None:
        """Credit each truck's (and station's) unfinished activity at the end.

        Must be called after ``engine.run(until)`` returns.

        Args:
            until: The simulation end time (minutes).
        """
        for truck in self.trucks:
            elapsed = self._credit_elapsed(truck, until)
            self.logger.debug(
                "Truck %d still %s at end; credited %.0f min",
                truck.id,
                truck._state.name,
                elapsed,
            )
            if truck._state is TruckState.UNLOADING:
                assert truck._station_id is not None
                self.stations[truck._station_id].time_busy += elapsed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _credit_elapsed(self, truck: MiningTruck, now: float | None = None) -> float:
        """Add time since the truck's state began to that state's total.

        Args:
            truck: The truck to credit.
            now:   Override for the current time; defaults to engine clock.

        Returns:
            The elapsed minutes since the truck's state began.
        """
        current_time = now if now is not None else self.engine.clock
        elapsed = current_time - truck._state_start
        # Look up which time-total attribute corresponds to the current state
        # and increment it, avoiding a separate if/elif for each TruckState.
        total = _STATE_TOTALS[truck._state]
        setattr(truck, total, getattr(truck, total) + elapsed)
        truck._state_start = current_time
        return elapsed

    def _transition(self, truck: MiningTruck, next_state: TruckState) -> float:
        """Close out the truck's current state and enter ``next_state``.

        Returns the minutes spent in the state that just ended.
        """
        elapsed = self._credit_elapsed(truck)
        truck._state = next_state
        return elapsed

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_mining_complete(self, truck_id: int) -> None:
        """Truck finishes mining -> record time, start traveling to station."""
        truck = self.trucks[truck_id]
        self._transition(truck, TruckState.TRAVELING)

        self.logger.debug(
            "t=%.0f MINING_COMPLETE truck=%d station=None",
            self.engine.clock,
            truck_id,
        )

        self.engine.schedule(
            self.engine.clock + TRAVEL_TIME_MINUTES,
            functools.partial(self._on_arrive_station, truck_id),
            label=f"ARRIVE_STATION truck={truck_id}",
        )

    def _on_arrive_station(self, truck_id: int) -> None:
        """Truck arrives at station area -> pick best station, schedule unload.

        The truck is assigned to the station with the earliest
        ``available_at`` timestamp. The unload duration is pre-rolled so
        the station's ``available_at`` can be updated immediately,
        allowing subsequent trucks to make informed queue choices.
        """
        truck = self.trucks[truck_id]
        self._transition(truck, TruckState.WAITING)

        self.logger.debug(
            "t=%.0f ARRIVE_STATION truck=%d station=None",
            self.engine.clock,
            truck_id,
        )

        # Pick station with the shortest wait
        best_station = min(self.stations, key=lambda s: s.available_at)
        # max() handles both cases: station free now (available_at <= clock)
        # means unloading starts immediately; station busy means the truck waits.
        unload_start = max(self.engine.clock, best_station.available_at)
        unload_duration = self.rng.randint(MIN_UNLOAD_MINUTES, MAX_UNLOAD_MINUTES)
        # Advance the station's availability by this truck's unload duration so
        # subsequent arrivals can calculate their wait without an explicit queue.
        best_station.available_at = unload_start + unload_duration
        truck._station_id = best_station.id
        self.logger.debug(
            "Truck %d assigned to station %d: wait %.0f min, unload %d min",
            truck_id,
            best_station.id,
            unload_start - self.engine.clock,
            unload_duration,
        )

        # Schedule the start and finish of unloading
        self.engine.schedule(
            float(unload_start),
            functools.partial(self._on_start_unload, truck_id, best_station.id),
            label=f"START_UNLOAD truck={truck_id} station={best_station.id}",
        )
        self.engine.schedule(
            float(unload_start + unload_duration),
            functools.partial(self._on_finish_unload, truck_id, best_station.id),
            label=f"FINISH_UNLOAD truck={truck_id} station={best_station.id}",
        )

    def _on_start_unload(self, truck_id: int, station_id: int) -> None:
        """Station becomes available for this truck -> record wait time."""
        truck = self.trucks[truck_id]
        self._transition(truck, TruckState.UNLOADING)

        self.logger.debug(
            "t=%.0f START_UNLOAD truck=%d station=%d",
            self.engine.clock,
            truck_id,
            station_id,
        )

    def _on_finish_unload(self, truck_id: int, station_id: int) -> None:
        """Truck finishes unloading -> record stats, head back to mine."""
        truck = self.trucks[truck_id]
        station = self.stations[station_id]

        self.logger.debug(
            "t=%.0f FINISH_UNLOAD truck=%d station=%d",
            self.engine.clock,
            truck_id,
            station_id,
        )

        # _transition() returns the minutes just spent in the ending state
        # (UNLOADING), which is exactly the time this station was busy for
        # this truck - credited here rather than at START_UNLOAD so we have
        # the precise elapsed duration rather than re-deriving it.
        unload_time = self._transition(truck, TruckState.TRAVELING)
        truck.loads_delivered += 1
        truck._station_id = None
        station.trucks_served += 1
        station.time_busy += unload_time

        # Travel back to a mining site
        self.engine.schedule(
            self.engine.clock + TRAVEL_TIME_MINUTES,
            functools.partial(self._on_arrive_mine, truck_id),
            label=f"ARRIVE_MINE truck={truck_id}",
        )

    def _on_arrive_mine(self, truck_id: int) -> None:
        """Truck arrives at a mining site -> record travel, start mining."""
        truck = self.trucks[truck_id]
        self._transition(truck, TruckState.MINING)

        self.logger.debug(
            "t=%.0f ARRIVE_MINE truck=%d station=None",
            self.engine.clock,
            truck_id,
        )

        duration = (
            self.rng.randint(MIN_MINING_HOURS, MAX_MINING_HOURS)
            * HOURS_TO_MINUTES
        )
        self.logger.debug(
            "Truck %d arrived at mine: will mine for %d min",
            truck_id,
            duration,
        )
        self.engine.schedule(
            self.engine.clock + duration,
            functools.partial(self._on_mining_complete, truck_id),
            label=f"MINING_COMPLETE truck={truck_id}",
        )
