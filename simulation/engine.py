"""Discrete-event simulation engine for the lunar He-3 mining operation."""

import heapq
import logging
import random
from typing import Callable, ClassVar

from .config import (
    HOURS_TO_MINUTES,
    MAX_MINING_HOURS,
    MAX_UNLOAD_MINUTES,
    MIN_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    TRAVEL_TIME_MINUTES,
    SimConfig,
)
from .models import Event, EventType, MiningTruck, TruckState, UnloadStation

logger = logging.getLogger(__name__)

# The MiningTruck attribute that accumulates time spent in each state.
_STATE_TOTALS = {
    TruckState.MINING: "time_mining",
    TruckState.TRAVELING: "time_traveling",
    TruckState.WAITING: "time_waiting",
    TruckState.UNLOADING: "time_unloading",
}


class SimulationEngine:
    """Runs the mining simulation using a priority-queue event loop.

    The engine owns the simulation clock, the event queue, and all entity
    instances (trucks and stations).  Call :meth:`run` once to execute the
    simulation from start to finish; create a new engine for another run.

    Attributes:
        config:      Immutable simulation parameters.
        clock:       Current simulation time in minutes.
        trucks:      List of all mining trucks.
        stations:    List of all unload stations.
    """

    def __init__(self, config: SimConfig) -> None:
        self.config = config
        self.clock: float = 0.0
        self.rng = random.Random(config.random_seed)
        self.event_queue: list[Event] = []
        self._has_run = False

        self.trucks = [MiningTruck(id=i) for i in range(config.num_trucks)]
        self.stations = [UnloadStation(id=i) for i in range(config.num_stations)]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the simulation to completion.

        Initialises all trucks at mining sites, then processes events in
        chronological order until the event queue is empty or the next
        event falls beyond the configured duration.  Activities still in
        progress at the end are credited up to the end time.

        Raises:
            RuntimeError: If called more than once on the same engine.
        """
        if self._has_run:
            raise RuntimeError(
                "SimulationEngine.run() can only be called once; "
                "create a new engine for another run."
            )
        self._has_run = True

        config = self.config
        logger.info(
            "Starting simulation: %d trucks, %d stations, %d h (seed=%s)",
            config.num_trucks, config.num_stations, config.duration_hours, config.random_seed,
        )

        end_time = config.duration_minutes
        events_processed = 0
        self._initialize_events()
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > end_time:
                heapq.heappush(self.event_queue, event)
                break
            self.clock = event.time
            self._dispatch(event)
            events_processed += 1

        logger.debug(
            "%d events scheduled after t=%.0f were not processed",
            len(self.event_queue), end_time,
        )
        self.clock = end_time
        self._credit_in_progress_activities()

        logger.info(
            "Simulation finished at t=%.0f min: %d events processed, %d loads delivered",
            self.clock, events_processed, sum(t.loads_delivered for t in self.trucks),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _initialize_events(self) -> None:
        """Schedule the first MINING_COMPLETE event for every truck.

        All trucks start empty at a mining site at t=0.  Each truck's
        initial mining duration is drawn randomly from [1, 5] hours.
        """
        for truck in self.trucks:
            duration = (
                self.rng.randint(MIN_MINING_HOURS, MAX_MINING_HOURS)
                * HOURS_TO_MINUTES
            )
            self._schedule(Event(
                time=duration,
                type=EventType.MINING_COMPLETE,
                truck_id=truck.id,
            ))

    def _schedule(self, event: Event) -> None:
        """Push an event onto the priority queue."""
        heapq.heappush(self.event_queue, event)

    def _credit_elapsed(self, truck: MiningTruck) -> float:
        """Add time since the truck's state began to that state's total."""
        elapsed = self.clock - truck._state_start
        total = _STATE_TOTALS[truck._state]
        setattr(truck, total, getattr(truck, total) + elapsed)
        truck._state_start = self.clock
        return elapsed

    def _transition(self, truck: MiningTruck, next_state: TruckState) -> float:
        """Close out the truck's current state and enter ``next_state``.

        Returns the minutes spent in the state that just ended.
        """
        elapsed = self._credit_elapsed(truck)
        truck._state = next_state
        return elapsed

    def _credit_in_progress_activities(self) -> None:
        """Credit each truck's (and station's) unfinished activity at the end."""
        for truck in self.trucks:
            elapsed = self._credit_elapsed(truck)
            logger.debug(
                "Truck %d still %s at end; credited %.0f min",
                truck.id, truck._state.name, elapsed,
            )
            if truck._state is TruckState.UNLOADING:
                assert truck._station_id is not None
                self.stations[truck._station_id].time_busy += elapsed

    def _dispatch(self, event: Event) -> None:
        """Route an event to the appropriate handler method."""
        logger.debug(
            "t=%.0f %s truck=%d station=%s",
            event.time, event.type.name, event.truck_id, event.station_id,
        )
        handler = self._HANDLERS[event.type]
        handler(self, event)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_mining_complete(self, event: Event) -> None:
        """Truck finishes mining → record time, start traveling to station."""
        truck = self.trucks[event.truck_id]
        self._transition(truck, TruckState.TRAVELING)

        self._schedule(Event(
            time=self.clock + TRAVEL_TIME_MINUTES,
            type=EventType.ARRIVE_STATION,
            truck_id=truck.id,
        ))

    def _on_arrive_station(self, event: Event) -> None:
        """Truck arrives at station area → pick best station, schedule unload.

        The truck is assigned to the station with the earliest
        ``available_at`` timestamp.  The unload duration is pre-rolled so
        the station's ``available_at`` can be updated immediately,
        allowing subsequent trucks to make informed queue choices.
        """
        truck = self.trucks[event.truck_id]
        self._transition(truck, TruckState.WAITING)

        # Pick station with the shortest wait
        best_station = min(self.stations, key=lambda s: s.available_at)
        unload_start = max(self.clock, best_station.available_at)
        unload_duration = self.rng.randint(MIN_UNLOAD_MINUTES, MAX_UNLOAD_MINUTES)
        best_station.available_at = unload_start + unload_duration
        truck._station_id = best_station.id
        logger.debug(
            "Truck %d assigned to station %d: wait %.0f min, unload %d min",
            truck.id, best_station.id, unload_start - self.clock, unload_duration,
        )

        # Schedule the start and finish of unloading
        self._schedule(Event(
            time=unload_start,
            type=EventType.START_UNLOAD,
            truck_id=truck.id,
            station_id=best_station.id,
        ))
        self._schedule(Event(
            time=unload_start + unload_duration,
            type=EventType.FINISH_UNLOAD,
            truck_id=truck.id,
            station_id=best_station.id,
        ))

    def _on_start_unload(self, event: Event) -> None:
        """Station becomes available for this truck → record wait time."""
        truck = self.trucks[event.truck_id]
        self._transition(truck, TruckState.UNLOADING)

    def _on_finish_unload(self, event: Event) -> None:
        """Truck finishes unloading → record stats, head back to mine."""
        truck = self.trucks[event.truck_id]
        assert event.station_id is not None
        station = self.stations[event.station_id]

        unload_time = self._transition(truck, TruckState.TRAVELING)
        truck.loads_delivered += 1
        truck._station_id = None
        station.trucks_served += 1
        station.time_busy += unload_time

        # Travel back to a mining site
        self._schedule(Event(
            time=self.clock + TRAVEL_TIME_MINUTES,
            type=EventType.ARRIVE_MINE,
            truck_id=truck.id,
        ))

    def _on_arrive_mine(self, event: Event) -> None:
        """Truck arrives at a mining site → record travel, start mining."""
        truck = self.trucks[event.truck_id]
        self._transition(truck, TruckState.MINING)

        duration = (
            self.rng.randint(MIN_MINING_HOURS, MAX_MINING_HOURS)
            * HOURS_TO_MINUTES
        )
        self._schedule(Event(
            time=self.clock + duration,
            type=EventType.MINING_COMPLETE,
            truck_id=truck.id,
        ))

    # Handler dispatch table (avoids if/elif chains)
    _HANDLERS: ClassVar[dict[EventType, Callable[["SimulationEngine", Event], None]]] = {
        EventType.MINING_COMPLETE: _on_mining_complete,
        EventType.ARRIVE_STATION: _on_arrive_station,
        EventType.START_UNLOAD: _on_start_unload,
        EventType.FINISH_UNLOAD: _on_finish_unload,
        EventType.ARRIVE_MINE: _on_arrive_mine,
    }
