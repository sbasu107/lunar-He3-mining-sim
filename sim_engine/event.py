"""Event and EventHandle primitives for the discrete-event simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class EventHandle:
    """Opaque handle returned by :meth:`SimulationEngine.schedule`.

    Call :meth:`cancel` before the event fires to prevent its action from
    executing. Once cancelled, the event is silently skipped when popped
    from the priority queue.
    """

    _cancelled: bool = field(default=False, repr=False)

    def cancel(self) -> None:
        """Mark the associated event as cancelled."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """Whether :meth:`cancel` has been called."""
        return self._cancelled


@dataclass(order=True)
class Event:
    """A single scheduled event in the simulation.

    Only ``(time, seq)`` participate in ordering so that :mod:`heapq`
    sorts events chronologically with deterministic FIFO tie-breaking.
    """

    time: float
    seq: int
    action: Callable[[], None] = field(compare=False, repr=False)
    handle: EventHandle = field(compare=False, repr=False)
    label: str = field(default="", compare=False)

    def __repr__(self) -> str:
        cancelled = " CANCELLED" if self.handle.is_cancelled else ""
        return f"Event(t={self.time:.1f}, seq={self.seq}, label={self.label!r}{cancelled})"
