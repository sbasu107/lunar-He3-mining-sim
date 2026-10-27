"""Data models for the mining domain: truck states, event types, trucks, and stations."""

from dataclasses import dataclass, field
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class TruckState(Enum):
    """What a truck is currently doing; each state has its own time total."""

    MINING = auto()
    TRAVELING = auto()
    WAITING = auto()
    UNLOADING = auto()


class MiningEventType(Enum):
    """Every distinct moment in a truck's operating cycle."""

    MINING_COMPLETE = auto()   # Truck finishes mining at a site
    ARRIVE_STATION = auto()    # Truck arrives at the unload station area
    START_UNLOAD = auto()      # Truck begins unloading (may wait first)
    FINISH_UNLOAD = auto()     # Truck finishes unloading
    ARRIVE_MINE = auto()       # Truck arrives back at a mining site


# ---------------------------------------------------------------------------
# Mining Truck
# ---------------------------------------------------------------------------
@dataclass
class MiningTruck:
    """Tracks a single truck's identity and cumulative operating statistics.

    All time values are stored in **minutes**.

    Attributes:
        id:              Unique truck identifier.
        loads_delivered:  Number of completed unload cycles.
        time_mining:     Total minutes spent mining.
        time_traveling:  Total minutes spent traveling (both directions).
        time_waiting:    Total minutes spent waiting in a station queue.
        time_unloading:  Total minutes spent unloading at a station.
    """

    id: int

    # Cumulative statistics
    loads_delivered: int = 0
    time_mining: float = 0.0
    time_traveling: float = 0.0
    time_waiting: float = 0.0
    time_unloading: float = 0.0

    # Internal bookkeeping — the current state, when it began, and the station
    # the truck is assigned to (if any), so the engine can credit elapsed time
    # when the state changes or the simulation ends.
    _state: TruckState = field(default=TruckState.MINING, repr=False)
    _state_start: float = field(default=0.0, repr=False)
    _station_id: int | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Unload Station
# ---------------------------------------------------------------------------
@dataclass
class UnloadStation:
    """Tracks a single unload station's availability and statistics.

    Instead of maintaining an explicit queue of waiting trucks, each station
    records the time at which it will next be free (``available_at``).  A
    truck arriving at the station area picks the station with the smallest
    ``available_at`` — this gives the same result as an explicit shortest-
    queue strategy while being simpler to implement.

    Attributes:
        id:             Unique station identifier.
        available_at:   Time (in minutes) when this station will next be free.
        trucks_served:  Number of trucks that have completed unloading here.
        time_busy:      Total minutes this station spent actively unloading.
    """

    id: int
    available_at: float = 0.0
    trucks_served: int = 0
    time_busy: float = 0.0
