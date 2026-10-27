# Goldfish Annotated Review Report

* **Status:** Resolved
* **Target:** `design_draft.md` (`FeatureRange`: Lines 1–253)

## Prioritized Findings & AI Suggestions

### 1. Station Busy-Time Reconciliation Failure [`egm-design`] - Severity: High
* **Affected Scope:** [Lines 58, 103–104, 128–135, 169–171, 219–221](design_draft.md#L58) (`Technical Plan & Models`)
* **Discrepancy Description:** `MiningTruck` and `UnloadStation` independently implementing `SimulationListener.on_simulation_end(clock)` breaks because `UnloadStation` only stores `available_at` (including queued trucks) and has no reference to which truck is docked or when active unloading began.
* **Rationale:** An isolated station listener cannot calculate its active busy time from `available_at` at $t = \text{until}$.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Because `SimulationEngine.run(until)` is synchronous, domain-wide reconciliation does not need an observer pattern on individual entities. `MiningSimulation.finalize(until)` can coordinate truck and station reconciliation in a single pass when `run()` returns.
* ***Proposed Edit:***
  * Location: `### Architectural Overview`, `### Component Details`
  * Change: Remove `SimulationListener` from `MiningTruck` and `UnloadStation`. Designate `MiningSimulation` to coordinate end-of-simulation reconciliation across trucks and stations via a `finalize(until: float)` method called post-run.

---

### 2. Non-Deterministic Priority Queue Tie-Breaking [`egm-design`] - Severity: High
* **Affected Scope:** [Lines 119–126, 149–152](design_draft.md#L119-L126) (`sim_engine/event.py` & `engine.py`)
* **Discrepancy Description:** `@dataclass(order=True)` with only `time` participating in comparison does not guarantee FIFO order for identical timestamps in Python's `heapq`.
* **Rationale:** Ties in min-heap sift operations produce arbitrary execution order, violating strict determinism requirements.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Adding an auto-incrementing integer sequence counter `seq` ensures guaranteed FIFO order for events scheduled at the exact same simulation time.
* ***Proposed Edit:***
  * Location: `sim_engine/event.py` and `sim_engine/engine.py`
  * Change: Define `Event(time: float, seq: int, action: Callable[[], None], label: str = "")` where `(time, seq)` order the priority queue, with `SimulationEngine` maintaining an internal `_seq` counter.

---

### 3. Breaking API Contract for `Reporter` and Legacy Compatibility [`egm-design`] - Severity: Medium
* **Affected Scope:** [Lines 189–191, 199–203](design_draft.md#L189-L203) (`mining/reporting.py` & `main.py`)
* **Discrepancy Description:** Changing `Reporter.__init__` to accept `(trucks, stations, duration_hours)` breaks existing unit tests that instantiate `Reporter(engine)`.
* **Rationale:** Existing test suites expect `Reporter` to accept a simulation engine instance.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Supporting polymorphic constructor arguments allows new code to pass explicit entity lists while maintaining 100% test compatibility for existing tests.
* ***Proposed Edit:***
  * Location: `mining/reporting.py`
  * Change: Implement polymorphic initialization: `Reporter(target: Any = None, *, trucks=None, stations=None, duration_hours=None)`.

---

### 4. Virtual Time Monotonicity, Past-Time Guards, and Peeking Semantics [`egm-design`] - Severity: Medium
* **Affected Scope:** [Lines 149–162, 208–221](design_draft.md#L149-L162) (`sim_engine/engine.py`)
* **Discrepancy Description:** `schedule()` lacks a guard against scheduling in the virtual past ($t < \text{clock}$), and cutoff check pops events before checking `event.time > until`.
* **Rationale:** Scheduling in the past violates DES causality; popping future events drops them from the queue.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** A guard ensures monotonicity, and peeking (`self._queue[0].time > until`) halts cleanly without destructive pops.
* ***Proposed Edit:***
  * Location: `sim_engine/engine.py`
  * Change: Add `if time < self.clock: raise ValueError(...)` in `schedule()`. In `run()`, peek at `self._queue[0].time > until` before popping.

---

### 5. Missing Trade-Off Evaluation Table in Alternatives Considered [`egm-structural`] - Severity: Medium
* **Affected Scope:** [Lines 225–251](design_draft.md#L225-L251) (`## Alternatives Considered`)
* **Discrepancy Description:** The section contains detailed prose for Alternatives A–D but omits a trade-off comparison matrix required by `feature-spec-standard`.
* **Rationale:** A summary table enables rapid scanning of technical trade-offs across options.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** A comparative markdown table provides structured clarity before narrative details.
* ***Proposed Edit:***
  * Location: Start of `## Alternatives Considered`
  * Change: Insert a Markdown table comparing Alternatives A, B, C, and D across External Dependencies, Simplicity, Dispatch Overhead, and Selection Decision.

---

### 6. Missing Explicit `## Open Questions` Section [`egm-structural`] - Severity: Medium
* **Affected Scope:** Post-Line 250 (`Feature Specification Scope`)
* **Discrepancy Description:** Replacing `## Open Questions` with `## Resolved Decisions` omitted the required section certifying that no unresolved questions remain.
* **Rationale:** Feature specification templates require an explicit `## Open Questions` section.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Explicitly stating "None" confirms all technical questions are resolved.
* ***Proposed Edit:***
  * Location: Before `## Critical User Journeys`
  * Change: Add `## Open Questions` with entry `* None (all open architectural questions resolved during brainstorming and review)`.

---

### 7. Section Hierarchy and Placement of `## Resolved Decisions` [`egm-structural`] - Severity: Medium
* **Affected Scope:** [Lines 56–62](design_draft.md#L56-L62)
* **Discrepancy Description:** Placing `## Resolved Decisions` before CUJs and Technical Architecture disrupts the standard requirements-to-design hierarchy.
* **Rationale:** Decisions should follow the Technical Architecture and Alternatives sections they resolve.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Moving Resolved Decisions after Alternatives Considered restores logical document progression.
* ***Proposed Edit:***
  * Location: Move from Line 56 to after `## Alternatives Considered`.

---

### 8. Sub-Section Structural Asymmetry in Component Details [`egm-structural`] - Severity: Medium
* **Affected Scope:** [Lines 110–204](design_draft.md#L110-L204) (`### Component Details`)
* **Discrepancy Description:** Subsection 1 uses code snippets, Subsection 2 uses deeply nested bullets without code, and Subsection 3 has no breakdown.
* **Rationale:** Structural symmetry requires uniform layout across sibling subsections.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Standardize all three subsections to follow a unified pattern (Responsibilities, Component Breakdown, API Signature/Schema).
* ***Proposed Edit:***
  * Location: `### Component Details`
  * Change: Standardize subsections 1, 2, and 3 to follow identical structure.

---

### 9. Colloquial Phrasing and Buzzwords [`egm-style`] - Severity: Medium
* **Affected Scope:** [Lines 28, 30, 58–59](design_draft.md#L28-L59) (`Problem & Decisions`)
* **Discrepancy Description:** Use of informal language ("shoehorning"), subjective adjectives ("clean"), mixed metaphors ("mid-flight activities"), and redundant intensifiers ("fully deterministic and reproducible").
* **Rationale:** Technical specifications require dry, precise, objective language.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Clean copy editing brings prose into compliance with professional engineering standards.
* ***Proposed Edit:***
  * Location: Lines 28, 30, 58, 59
  * Change: Replace with "integrating unrelated domain models", "standalone discrete-event kernel", "in-progress activities", and "deterministic execution".

---

### 10. Lack of Event Cancellation Primitive in Core Kernel [`egm-design`] - Severity: Low
* **Affected Scope:** [Lines 119–126, 149–152](design_draft.md#L119-L152) (`sim_engine/event.py`)
* **Discrepancy Description:** `schedule()` returns nothing and does not provide an event cancellation handle.
* **Rationale:** Rescheduling or aborting tasks is common in operational simulations.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Returning an `EventHandle(cancel())` adds cancellation support with minimal overhead.
* ***Proposed Edit:***
  * Location: `sim_engine/event.py` and `sim_engine/engine.py`
  * Change: Define `EventHandle` with `cancel()` method, checked in the dispatch loop.

---

### 11. Redundant Metadata Fields on `Event` [`egm-design`, `egm-style`] - Severity: Low
* **Affected Scope:** [Lines 123–126](design_draft.md#L123-L126) (`sim_engine/event.py`)
* **Discrepancy Description:** Having both `event_type: Any` and `description: str` is redundant when using the Command pattern.
* **Rationale:** A single descriptive label is cleaner for logging.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Simplify `Event` metadata to `label: str = ""`.
* ***Proposed Edit:***
  * Location: `sim_engine/event.py`
  * Change: Replace `event_type` and `description` with `label: str = ""`.

---

### 12. Markdown Formatting, Thematic Breaks, and Hyperlinks [`egm-structural`] - Severity: Low
* **Affected Scope:** Lines 7, 17, 21, 30, 32, 44, 49, 179–183, 209–220, 230
* **Discrepancy Description:** 80-character hyphen lines (`---...---`), inconsistent bullet markers (`*` vs `-`), and unlinked file references (`instructions.md`, `main.py`).
* **Rationale:** Markdown standards dictate consistent thematic breaks (`---`), uniform bullet syntax, and clickable relative links.
* ***AI Suggestion:*** `PROPOSE FIX`
* ***Justification:** Enhances visual consistency and document navigability.
* ***Proposed Edit:***
  * Location: Throughout lines 1–253
  * Change: Replace divider lines with standard `---`, unify list markers, and add relative Markdown links to project files.
