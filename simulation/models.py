"""Backward-compatibility facade for simulation models."""

from dataclasses import dataclass, field

from mining.models import (
    MiningEventType,
    MiningTruck,
    TruckState,
    UnloadStation,
)

EventType = MiningEventType


@dataclass(order=True)
class Event:
    """Legacy simulation event model retained for backward compatibility."""

    time: float
    type: EventType = field(compare=False)
    truck_id: int = field(compare=False)
    station_id: int | None = field(default=None, compare=False)

    def __repr__(self) -> str:
        station = f", station={self.station_id}" if self.station_id is not None else ""
        return f"Event(t={self.time:.1f}, {self.type.name}, truck={self.truck_id}{station})"


__all__ = [
    "Event",
    "EventType",
    "MiningEventType",
    "MiningTruck",
    "TruckState",
    "UnloadStation",
]
