# `sim_engine` package

A minimal, domain-agnostic discrete-event simulation engine implemented with Python standard library components.

## Overview

`sim_engine` manages:
- **Virtual Clock**: Advances discrete virtual time strictly to scheduled event timestamps.
- **Priority Queue**: Uses Python's `heapq` for logarithmic event scheduling and retrieval.
- **Deterministic Tie-Breaking**: Incorporates a monotonic sequence counter (`seq`) to guarantee reproducible FIFO ordering when events share identical timestamps.
- **Event Cancellation**: Returns an `EventHandle` upon scheduling to allow clean event revocation before execution.
- **Zero Domain Assumptions**: Zero imports or knowledge of trucks, queues, or lunar operations.

## Architecture & API

### Core Primitives

- `EventHandle`: Opaque controller returned when scheduling an event. Provides `.cancel()` and `.is_cancelled`.
- `Event`: Priority queue element ordered strictly by `(time, seq)`. Carries a zero-argument callable `action`.
- `SimulationEngine`: Central scheduler.
  - `schedule(time: float, action: Callable[[], None], label: str = "") -> EventHandle`
  - `run(until: float) -> None`
  - `clock: float` (current virtual time)
  - `pending_count: int` (remaining queue size)

## Example Usage

```python
from sim_engine import SimulationEngine

engine = SimulationEngine()

def greet(name: str):
    print(f"[{engine.clock:.1f}m] Hello, {name}!")

# Schedule events
engine.schedule(10.0, lambda: greet("Alice"), label="greet_alice")
handle = engine.schedule(20.0, lambda: greet("Bob"), label="greet_bob")
engine.schedule(20.0, lambda: greet("Charlie"), label="greet_charlie")

# Cancel Bob's greeting
handle.cancel()

# Run the simulation
engine.run(until=30.0)
# Output:
# [10.0m] Hello, Alice!
# [20.0m] Hello, Charlie!
```
