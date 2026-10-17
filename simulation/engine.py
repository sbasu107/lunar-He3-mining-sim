"""Discrete-event simulation engine for the lunar He-3 mining operation."""

import heapq
import random

from .config import (
    SimConfig,
    HOURS_TO_MINUTES,
    TRAVEL_TIME_MINUTES,
    MIN_MINING_HOURS,
    MAX_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    MAX_UNLOAD_MINUTES,
)
from .models import Event, EventType, MiningTruck, UnloadStation


class SimulationEngine:
    """Runs the mining simulation using a priority-queue event loop.

    The engine owns the simulation clock, the event queue, and all entity
    instances (trucks and stations).  Call :meth:`run` to execute the
    simulation from start to finish.

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

        self.trucks = [MiningTruck(id=i) for i in range(config.num_trucks)]
        self.stations = [UnloadStation(id=i) for i in range(config.num_stations)]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the simulation to completion.

        Initialises all trucks at mining sites, then processes events in
        chronological order until the event queue is empty or the next
        event falls beyond the configured duration.
        """
        self._initialize_events()
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > self.config.duration_minutes:
                break
            self.clock = event.time
            self._dispatch(event)

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

    def _dispatch(self, event: Event) -> None:
        """Route an event to the appropriate handler method."""
        handler = self._HANDLERS[event.type]
        handler(self, event)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_mining_complete(self, event: Event) -> None:
        """Truck finishes mining → record time, start traveling to station."""
        truck = self.trucks[event.truck_id]
        truck.time_mining += self.clock - truck._state_start
        truck._state_start = self.clock

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
        truck.time_traveling += TRAVEL_TIME_MINUTES

        # Pick station with the shortest wait
        best_station = min(self.stations, key=lambda s: s.available_at)
        unload_start = max(self.clock, best_station.available_at)
        unload_duration = self.rng.randint(MIN_UNLOAD_MINUTES, MAX_UNLOAD_MINUTES)
        best_station.available_at = unload_start + unload_duration

        truck._state_start = self.clock  # waiting begins now

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
        truck.time_waiting += self.clock - truck._state_start
        truck._state_start = self.clock

    def _on_finish_unload(self, event: Event) -> None:
        """Truck finishes unloading → record stats, head back to mine."""
        truck = self.trucks[event.truck_id]
        station = self.stations[event.station_id]

        unload_time = self.clock - truck._state_start
        truck.time_unloading += unload_time
        truck.loads_delivered += 1
        station.trucks_served += 1
        station.time_busy += unload_time

        truck._state_start = self.clock

        # Travel back to a mining site
        self._schedule(Event(
            time=self.clock + TRAVEL_TIME_MINUTES,
            type=EventType.ARRIVE_MINE,
            truck_id=truck.id,
        ))

    def _on_arrive_mine(self, event: Event) -> None:
        """Truck arrives at a mining site → record travel, start mining."""
        truck = self.trucks[event.truck_id]
        truck.time_traveling += TRAVEL_TIME_MINUTES

        duration = (
            self.rng.randint(MIN_MINING_HOURS, MAX_MINING_HOURS)
            * HOURS_TO_MINUTES
        )
        truck._state_start = self.clock
        self._schedule(Event(
            time=self.clock + duration,
            type=EventType.MINING_COMPLETE,
            truck_id=truck.id,
        ))

    # Handler dispatch table (avoids if/elif chains)
    _HANDLERS = {
        EventType.MINING_COMPLETE: _on_mining_complete,
        EventType.ARRIVE_STATION: _on_arrive_station,
        EventType.START_UNLOAD: _on_start_unload,
        EventType.FINISH_UNLOAD: _on_finish_unload,
        EventType.ARRIVE_MINE: _on_arrive_mine,
    }
