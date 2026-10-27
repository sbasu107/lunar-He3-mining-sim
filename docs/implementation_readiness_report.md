# Implementation Readiness Audit Report (Stage 9)

**Target Document:** `design_draft.md`  
**Audited Scope:** Lines 386–543 (`DetailedRange`: Detailed Implementation Plan)  
**Standard:** `implementation-readiness-standard`  
**Reviewer Swarm:** `egm-implementation-readiness` (Tech Lead), `egm-codebase-details` (Codebase Auditor), `egm-style` (Copy Editor)

---

## Executive Summary

The Detailed Implementation Plan provides a coherent file-by-file breakdown, but pedantic inspection against the existing codebase and its 91 unit tests reveals critical omissions in the legacy facade adapters, CLI output contracts, and test assertions:
1. **Missing Legacy `Event` Definition in Compatibility Facade**: `tests/test_models.py` runs 5 tests asserting the legacy domain `Event(time, type, truck_id, station_id)` structure, which is incompatible with `sim_engine.Event(time, seq, action, handle, label)`.
2. **Dropped CLI Output Channels and Stderr Messages**: `main.py` omits required elapsed simulation time and output path prints to `stderr`, directly breaking assertions in `tests/test_cli.py`.
3. **Legacy `SimulationEngine` Adapter Incomplete Contracts**: The adapter lacks an `@rng.setter`, deferred `setup()` in parameterless `run()`, and `seed`/`config` attribute forwarding.
4. **Logger Namespace Contracts**: `tests/test_engine.py` asserts exact log records emitted under `"simulation.engine"`.
5. **Missing `SimConfig.__post_init__` Validation**: Validation ensuring positive integers for trucks, stations, and duration is omitted.

---

## Prioritized Findings

### Blockers (🔴 Execution-Halting Omissions)

#### 1. Missing Legacy `Event` Dataclass in `simulation/models.py`
* **Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Items 11 & 13 (`simulation/__init__.py`, `simulation/models.py`), Item 19 (`tests/test_models.py`)
* **Discrepancy Description:**
  `tests/test_models.py` (lines 49–76) contains `TestEvent` testing the legacy `Event(time, type, truck_id, station_id)` dataclass and its custom `__repr__`. `sim_engine.Event` has an incompatible signature (`time, seq, action, handle, label`). If `simulation.models` merely re-exports from `mining.models`, `Event` is missing; if it re-exports from `sim_engine`, `TestEvent` crashes with `TypeError`.
* **Recommendation:**
  Explicitly specify in Item 13 that `simulation/models.py` retains the legacy `Event(time, type, truck_id, station_id)` dataclass for backward compatibility, alias `EventType = MiningEventType`, and re-export both in `simulation/__init__.py`.

#### 2. Dropped CLI `stderr` Reporting and Status Messages in `main.py`
* **Reviewer:** `egm-codebase-details`
* **Affected Scope:** Item 15 (`main.py`), Architecture Section 3 (`main.py`)
* **Discrepancy Description:**
  `tests/test_cli.py` contains explicit assertions on `stderr` output:
  - `test_status_messages_go_to_stderr_not_stdout`: asserts `Simulated {hours} h in {elapsed * 1000:.1f} ms of real world time.` on `stderr`.
  - `test_output_flag_saves_same_report_as_stdout`: asserts `Report saved to {path}` on `stderr`.
  Dropping these messages causes immediate test failure.
* **Recommendation:**
  Include the exact `stderr` status prints in `main.py` and document them in Item 15.

---

### Major Findings (🟡 Architectural and Test Parity Risks)

#### 3. Legacy `SimulationEngine` Adapter Property and Lifecycle Contracts
* **Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Item 12 (`simulation/engine.py`), Step 3
* **Discrepancy Description:**
  `tests/test_engine.py` injects test doubles via attribute assignment (`engine.rng = StubRandom(...)`). If `SimulationEngine` does not define an `@rng.setter` forwarding to `MiningSimulation.rng`, an `AttributeError` is raised. Furthermore, if `scenario.setup()` runs in `__init__`, initial random draws occur before `StubRandom` can be injected.
* **Recommendation:**
  In Item 12, explicitly specify:
  1. Parameterless `run(self) -> None` that defaults to running until `self.config.duration_minutes`.
  2. Deferred execution: `run()` invokes `self._scenario.setup()` on first execution, runs the engine, and invokes `self._scenario.finalize()`.
  3. `@rng.setter` forwarding assignments to `self._scenario.rng`.
  4. Attribute forwarding for `clock`, `seed`, `config`, `trucks`, `stations`, and `event_queue`.

#### 4. Polymorphic `Reporter` Missing Seed and Config Parameters
* **Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Item 9 (`mining/reporting.py`), Section 3 (`mining/reporting.py`)
* **Discrepancy Description:**
  `Reporter.generate_markdown()` prints `- **Random Seed:** {seed}`. If initialized via keyword arguments without `seed` or `config`, the seed line is omitted, breaking CLI parity and failing `test_prints_report_for_requested_configuration`. Furthermore, `Reporter` provides 6 public metric calculation methods (`total_loads_delivered`, `system_throughput_loads_per_hour`, `truck_utilization`, `average_truck_utilization`, `station_utilization`, `average_station_utilization`) that must be documented.
* **Recommendation:**
  Update `Reporter.__init__` in Item 9 to accept `seed: int | None = None` and `config: SimConfig | None = None`, and document all 6 metric calculation methods.

#### 5. Logger Namespace Compatibility for `assertLogs("simulation.engine")`
* **Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`
* **Affected Scope:** Item 8 (`mining/scenario.py`), Item 12 (`simulation/engine.py`)
* **Discrepancy Description:**
  `tests/test_engine.py` (lines 393–428) runs 6 tests with `self.assertLogs("simulation.engine")` asserting exact log records for simulation start, dispatch, and finalization. If logs are emitted under `"mining.scenario"` or `"sim_engine.engine"`, `assertLogs("simulation.engine")` fails.
* **Recommendation:**
  Ensure the legacy adapter in `simulation/engine.py` configures or bridges logger records to `"simulation.engine"`, or document logger name preservation.

#### 6. Missing `SimConfig.__post_init__` Validation Logic
* **Reviewer:** `egm-codebase-details`
* **Affected Scope:** Item 6 (`mining/config.py`)
* **Discrepancy Description:**
  `tests/test_models.py` (lines 27–43) asserts that `SimConfig` raises `ValueError` if `num_trucks`, `num_stations`, or `duration_hours` are less than 1.
* **Recommendation:**
  Explicitly specify `SimConfig.__post_init__` validating positive integer values.

#### 7. Contradiction on Existing Test Suite Maintenance
* **Reviewer:** `egm-codebase-details`
* **Affected Scope:** Item 19 vs. Step 3
* **Discrepancy Description:**
  Item 19 states "Update imports ... across both direct packages and backward-compatibility facade", whereas Step 3 asserts "All existing 91 tests ... pass cleanly". Altering imports in `test_models.py` ceases to validate the compatibility facade.
* **Recommendation:**
  Keep all 91 existing unit tests importing from `simulation` to continuously validate the compatibility facade, while adding new tests `test_sim_engine.py` and `test_mining.py` to directly test the new packages.

---

### Nits (🟢 Style and Test Utilities)

#### 8. Shared Test Doubles Extraction
* **Reviewer:** `egm-codebase-details`
* **Affected Scope:** Item 18 (`tests/test_mining.py`)
* **Recommendation:**
  Extract `StubRandom` and `RecordingRandom` from `tests/test_engine.py` into a shared `tests/helpers.py` module to prevent duplicate double definitions.

#### 9. Virtual Time Cutoff Guard in `SimulationEngine.run(until)`
* **Reviewer:** `egm-codebase-details`
* **Affected Scope:** Item 3 (`sim_engine/engine.py`)
* **Recommendation:**
  Add a guard `if until < self.clock: raise ValueError(...)` to prevent the virtual clock from moving backwards.

#### 10. Copy Edit Claims and Absolute Wording
* **Reviewer:** `egm-style`
* **Affected Scope:** Lines 393, 403, 408, 436, 456, 465, 490, 494, 525, 536
* **Recommendation:**
  Replace hyperbolic or informal wording ("zero regressions", "100% test parity", "cleanly", "working seamlessly") with objective technical criteria.
