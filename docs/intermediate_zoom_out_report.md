# Intermediate Zoom-Out Architectural Review (Stage 8)

**Target Document:** `design_draft.md`  
**Reviewer:** Skeptical Architect (`egm-zoom-out`)  
**Standard:** `zoom-out-standard`

---

## Executive Summary

The revised design draft shows substantial architectural improvement:
* The complex `SimulationListener` observer pattern and registry have been replaced by a direct `finalize(until: float)` reconciliation pass on `MiningSimulation`.
* Stochastic logic (`rng`) has been cleanly separated from the core scheduler, keeping `sim_engine` purely deterministic and domain-agnostic.
* Monotonic sequence tie-breaking (`seq: int`) resolves priority queue determinism.
* Speculative future domain narratives have been removed.

However, the design draft still carries notable architectural bloat and YAGNI violations that prevent full adherence to the Zoom-Out Standard:
1. **Unnecessary Legacy Facade Layer (5 Files)**: Retaining the legacy `simulation/` directory and building a property-forwarding adapter layer for a self-contained internal repository with zero external consumers adds significant maintenance overhead.
2. **Speculative Event Cancellation Abstraction (`EventHandle`)**: Introducing a dedicated `EventHandle` class and checking cancellation in the inner dispatch loop when no mining feature ever cancels events.
3. **Multi-README Documentation Sprawl**: Proposing 5 separate README files across subpackages for a ~650-line Python codebase.
4. **Altitude Drops**: Embedding full Python method implementations (`main()`, `run()`) in architecture sections.

Addressing these findings simplifies the proposed footprint from 20 files down to ~7 clean files.

---

## Detailed Findings

### Finding 1: Unnecessary Backward-Compatibility Facade Layer (5 Files)
* **Severity**: Blocker
* **Affected Scope**: Target Files Items 11–14 (Lines 443–462), Implementation Sequence Step 3 (Lines 522–526)
* **Simplicity Rationale**:
  The draft retains the legacy `simulation/` directory (`__init__.py`, `engine.py`, `models.py`, `config.py`, `reporting.py`, and `simulation/README.md`) as a backward-compatibility facade wrapping `sim_engine` and `mining`. Item 12 proposes implementing `simulation/engine.py` as an adapter wrapping both packages with complex property forwarding for `clock`, `rng`, `trucks`, `stations`, and `event_queue`.

  This violates YAGNI:
  * **No External Consumers**: All call sites exist entirely within `main.py` and the 4 test files in `tests/`.
  * **Paradigm Mismatch**: The legacy `SimulationEngine` dispatches domain enum events (`EventType`) from its internal queue, while `sim_engine` dispatches domain-agnostic closures (`Callable[[], None]`). Shimming properties like `event_queue` across two completely different event models is fragile.
  * **Self-Contradictory Plan**: Item 19 already specifies updating test imports across `tests/test_models.py`, `tests/test_reporting.py`, `tests/test_cli.py`, and `tests/test_engine.py`. If test imports are being migrated anyway, the legacy facade serves no purpose.

  **Alternative**: Migrate `main.py` and existing tests directly to `mining` and `sim_engine`. Delete `simulation/` rather than maintaining a 5-file adapter layer.

---

### Finding 2: Speculative Event Cancellation Abstraction (`EventHandle`)
* **Severity**: Major
* **Affected Scope**: Section "Goals" (Line 41), "Component Details" (Lines 128–138, 145, 159, 162), "Implementation Plan" (Lines 397, 478)
* **Simplicity Rationale**:
  The draft introduces an `EventHandle` dataclass (`_cancelled: bool`, `cancel()`, `is_cancelled`), returns it from `SimulationEngine.schedule()`, attaches it to every `Event`, and checks `if event.handle.is_cancelled: continue` in the inner dispatch loop of `run()`.

  This is speculative ("YAGNI"):
  * Project requirements in `instructions.md` state that trucks *"remain in their chosen queue until unloaded."* In lunar He-3 mining, events are never cancelled or descheduled.
  * Zero methods in `mining/scenario.py` or `main.py` ever call `.cancel()`.
  * Allocating an `EventHandle` instance for every scheduled event adds unnecessary memory allocations and branching in the hot event loop for an unused feature.

  **Alternative**: Keep `Event` a simple dataclass `(time, seq, action, label)`. If event cancellation is needed in a future domain, it can be introduced when the concrete requirement arises.

---

### Finding 3: Multi-README Documentation Sprawl (5 README Files)
* **Severity**: Major
* **Affected Scope**: Target Files Items 4, 10, 14, 16, 20 (Lines 405–409, 438–442, 458–462, 468–472, 497–501)
* **Simplicity Rationale**:
  The proposal plans to create or modify 5 distinct README files (`sim_engine/README.md`, `mining/README.md`, `simulation/README.md`, `tests/README.md`, top-level `README.md`). For a ~650-line Python codebase, having a README inside every subpackage causes documentation sprawl and synchronization overhead.

  **Alternative**: Maintain a single, comprehensive top-level `README.md` that documents project architecture, package boundaries (`sim_engine` vs `mining`), CLI usage, and test commands. Omit subpackage READMEs.

---

### Finding 4: Altitude Drops in Component Details and Entry Point
* **Severity**: Nit
* **Affected Scope**: Section "Component Details" (Lines 151–182, 270–288, 298–321)
* **Simplicity Rationale**:
  The document drops into verbatim implementation code, copying complete Python function bodies (including full `main()` argument parsing, logging setup, and full `Reporter.__init__`).

  **Alternative**: Retain clear method signatures, type contracts, and flow diagrams; remove complete verbatim script implementations.

---

## Recommended Target Footprint (~7 Files)

```
lunar-He3-mining-sim/
├── sim_engine/
│   ├── __init__.py          # Exports SimulationEngine, Event
│   ├── engine.py            # Scheduler: clock, heapq, schedule(time, action, label), run(until)
│   └── event.py             # Event(time, seq, action, label)
├── mining/
│   ├── __init__.py          # Exports MiningSimulation, SimConfig, models, Reporter
│   ├── config.py            # SimConfig dataclass and operational constants
│   ├── models.py            # MiningTruck, UnloadStation, TruckState
│   ├── scenario.py          # MiningSimulation (event callbacks, shortest-wait queue, finalize)
│   └── reporting.py         # Formatted text and Markdown reporter
├── main.py                  # CLI entry point wiring sim_engine and mining
├── README.md                # Consolidated project & architecture documentation
└── tests/
    ├── test_sim_engine.py   # Isolated engine scheduler tests
    ├── test_mining.py       # Domain state machine and queue tests
    ├── test_models.py       # Entity dataclass tests
    ├── test_reporting.py    # Report formatting tests
    └── test_cli.py          # CLI argument and flag tests
```
