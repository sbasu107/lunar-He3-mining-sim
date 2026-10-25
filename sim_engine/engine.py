"""Domain-agnostic discrete-event simulation engine."""

from __future__ import annotations

import heapq
import logging
from typing import Callable

from .event import Event, EventHandle

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Minimal discrete-event scheduler.

    Manages a virtual clock, a priority queue of :class:`Event` objects,
    and a monotonic sequence counter for deterministic FIFO tie-breaking.

    The engine has **zero** knowledge of any domain (trucks, stations, etc.).
    Domain code schedules events via :meth:`schedule` and provides callbacks
    (closures) that encapsulate all domain-specific logic.

    Attributes:
        clock: Current virtual simulation time (minutes).
    """

    def __init__(self) -> None:
        self.clock: float = 0.0
        self._seq: int = 0
        self._queue: list[Event] = []
        self._has_run: bool = False
        self.events_processed: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule(
        self,
        time: float,
        action: Callable[[], None],
        label: str = "",
    ) -> EventHandle:
        """Schedule *action* to fire at virtual time *time*.

        Args:
            time: Virtual time (in minutes) when the action should execute.
                  Must not be earlier than the current clock.
            action: Zero-argument callable invoked when the event fires.
            label: Optional human-readable description for debugging.

        Returns:
            An :class:`EventHandle` that can cancel the event before it fires.

        Raises:
            ValueError: If *time* is in the virtual past.
        """
        if time < self.clock:
            raise ValueError(
                f"Cannot schedule event in the virtual past: "
                f"t={time} < clock={self.clock}"
            )
        handle = EventHandle()
        self._seq += 1
        event = Event(
            time=time,
            seq=self._seq,
            action=action,
            handle=handle,
            label=label,
        )
        heapq.heappush(self._queue, event)
        logger.debug("Scheduled %s", event)
        return handle

    def run(self, until: float) -> None:
        """Execute the event loop until virtual time *until*.

        Processes events in ``(time, seq)`` order. Events whose
        :attr:`EventHandle.is_cancelled` flag is set are silently skipped.
        The loop stops when the queue is empty or the next event's time
        exceeds *until*. After the loop, the clock is set to *until*.

        Args:
            until: Stop time for the simulation (inclusive).

        Raises:
            RuntimeError: If called more than once on the same engine.
        """
        if self._has_run:
            raise RuntimeError(
                "SimulationEngine.run() can only be called once; "
                "create a new engine for another run."
            )
        self._has_run = True

        events_processed = 0

        while self._queue:
            if self._queue[0].time > until:
                break
            event = heapq.heappop(self._queue)
            if event.handle.is_cancelled:
                continue
            self.clock = event.time
            event.action()
            events_processed += 1

        logger.debug(
            "%d events remain in queue after t=%.0f",
            len(self._queue),
            until,
        )
        self.clock = until
        self.events_processed = events_processed
        logger.debug(
            "Engine stopped: %d events processed, clock=%.0f",
            events_processed,
            self.clock,
        )

    @property
    def pending_count(self) -> int:
        """Number of events still in the queue (including cancelled ones)."""
        return len(self._queue)
