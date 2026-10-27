# Comprehension & Clarity Audit: `design_draft.md`

**Target File**: `design_draft.md`  
**Evaluated Scope**: Lines 1–418 (Feature Overview: 1–253, Detailed Plan: 254–417)  
**Auditor**: Comprehension Goldfish (Naive Reader Persona)

---

## Executive Summary

The architectural decoupling between `sim_engine` and `mining` is conceptually sound. However, from the perspective of a fresh reader with zero historical context, the document contains ambiguities regarding domain lifecycle contracts, unstated operational parameters, and implicit boundary conditions.

---

## Detailed Findings

### Finding 1: Unreconciled `UnloadStation` Lifecycle Protocol Contract
* **Severity**: Blocker
* **Affected Scope**: Technical Plan Architecture, Component Details, and Implementation Target 8 (`mining/models.py`)
* **Discrepancy Description & Rationale**:
  * The draft asserts that `UnloadStation` implements `SimulationListener` to "credit active unloading at simulation termination."
  * However, `SimulationListener.on_simulation_end(clock: float)` only accepts the cutoff `clock`. In the proposed model (and legacy `UnloadStation`), a station only tracks `available_at`, `trucks_served`, and `time_busy`. It holds no reference to which truck is currently docked or when the current unload began.
  * In the existing codebase, station busy time at cutoff is credited exclusively by inspecting `MiningTruck._state == TruckState.UNLOADING` and updating the assigned station from the truck.
  * An engineer cannot implement `UnloadStation.on_simulation_end(clock)` without either adding state tracking to `UnloadStation` (e.g., `busy_since: float | None`) or centralizing reconciliation in the domain coordinator (`MiningSimulation`).

---

### Finding 2: Undefined Truck State Machine and Lifecycle Transitions
* **Severity**: Major
* **Affected Scope**: Component Details (`mining/models.py`), Detailed Plan Target 8
* **Discrepancy Description & Rationale**:
  * The document notes that `MiningTruck` maintains `TruckState`, but never defines what states exist (`MINING`, `TRAVELING`, `WAITING`, `UNLOADING`).
  * While `MiningEventType` lists event names (`MINING_COMPLETE`, `ARRIVE_STATION`, `START_UNLOAD`, `FINISH_UNLOAD`, `ARRIVE_MINE`), the document does not map how events trigger transitions between truck states.

---

### Finding 3: Unstated Operational Constants, Timing Units, and Sampling Distributions
* **Severity**: Major
* **Affected Scope**: Component Details (`mining/config.py`), Data Flow
* **Discrepancy Description & Rationale**:
  * Constants are listed by name (`MIN_MINING_HOURS`, `MAX_MINING_HOURS`, `TRAVEL_TIME_MINUTES`, `MIN_UNLOAD_MINUTES`, `MAX_UNLOAD_MINUTES`, `HOURS_TO_MINUTES`), but their numerical values (1–5 hours, 30 minutes, 30–60 minutes) are omitted.
  * The probability distribution is not stated (discrete uniform random sampling with specified step resolution).
  * The base virtual clock unit (minutes) is not explicitly defined in the `sim_engine` specification.

---

### Finding 4: Ambiguity in `SimulationEngine.run(until)` Execution Semantics
* **Severity**: Major
* **Affected Scope**: `sim_engine/engine.py`, Detailed Plan Target 4
* **Discrepancy Description & Rationale**:
  * The boundary condition for `until` is ambiguous: whether `event.time == until` is dispatched or treated as cutoff.
  * The behavior of events scheduled beyond `until` remaining in the priority queue is not specified.
  * Repeated execution behavior (raising `RuntimeError` if called again) is not documented.

---

### Finding 5: Vague Heuristic for Station Selection and Queuing
* **Severity**: Major
* **Affected Scope**: `mining/scenario.py`, Alternative C
* **Discrepancy Description & Rationale**:
  * The document states that trucks pick the station with the shortest wait using `station.available_at`, but omits:
    1. How unload start time is calculated (`unload_start = max(self.clock, station.available_at)`).
    2. When `station.available_at` is updated (pre-advanced upon arrival by sampling duration).
    3. How ties are broken when multiple stations have identical availability (station with the lowest `id`).

---

### Finding 6: Priority Queue Tie-Breaking and Determinism
* **Severity**: Major
* **Affected Scope**: `sim_engine/event.py`, Detailed Plan Target 2
* **Discrepancy Description & Rationale**:
  * In Python's `heapq`, if two events have equal `time`, `Event.__lt__` returning `False` requires a secondary tie-breaker or sequence counter to ensure strict FIFO and reproducible execution across runs.

---

### Finding 7: Missing Clickable File Hyperlinks & Minor Diagram Gaps
* **Severity**: Nit
* **Affected Scope**: Entire Document
* **Discrepancy Description & Rationale**:
  * Several existing files (`instructions.md`, `main.py`, `simulation/engine.py`, `simulation/models.py`) are referenced as plain text without Markdown links.
  * The Mermaid diagram omits the dependency edge between `MiningSimulation` and `SimulationEngine`.
