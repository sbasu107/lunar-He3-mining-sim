# Critic Review Report (Stage 7)

**Target Document:** `design_draft.md`  
**Audited Scope:** Lines 1–253 (`FeatureRange`: Overview through Alternatives Considered)  
**Standard:** `feature-spec-standard`  
**Reviewer Swarm:** `egm-design` (Hostile Architecture), `egm-structural` (Document Architecture), `egm-style` (Copy Edit)

---

## Executive Summary

The architectural split between `sim_engine` and `mining` is conceptually sound, but the feature specification contains critical architectural flaws, structural layout gaps, and stylistic deficiencies that must be addressed:
1. **Station Busy-Time Reconciliation Failure**: Individual `SimulationListener` implementation on `MiningTruck` and `UnloadStation` fails because stations have no active truck or dock timestamp state.
2. **Priority Queue Non-Determinism**: Equal event timestamps in `heapq` lack a secondary monotonic sequence tie-breaker, causing non-deterministic event order.
3. **API & Test Suite Breakages**: Altering `Reporter.__init__` and lacking property forwarding on the legacy adapter will break existing unit tests.
4. **Structural & Layout Inconsistencies**: Missing open questions section, missing trade-off matrix in Alternatives Considered, decision/alternative asymmetry, and inconsistent subsection formatting.
5. **Colloquial & Promotional Phrasing**: Informal terminology ("shoehorning", "clean", "mid-flight activities") requires replacement with dry, objective technical language.

---

## Prioritized Findings

### Blockers (🔴 Critical Flaws)

#### 1. Station Busy-Time Reconciliation Failure via Individual Listeners
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 58, 103–104, 128–135, 169–171, 219–221
* **Discrepancy Description:**
  The design specifies that `MiningTruck` and `UnloadStation` independently implement `SimulationListener.on_simulation_end(clock: float)` to credit in-progress activities up to the simulation cutoff. In this simulation's model, `UnloadStation` only stores `available_at: float` (pre-rolled with queued unloads). The station does not store which truck is docked or when active unloading began. It is mathematically impossible for an isolated station listener to compute its active busy time from `available_at` at $t = \text{until}$. Furthermore, `MiningTruck` only stores `_station_id: int` without a reference to the stations collection.
* **Recommendation:**
  Do not register individual entities as engine listeners. Make the domain scenario manager (`MiningSimulation`) the sole `SimulationListener` (or call a direct reconciliation method `finalize(until)` after `engine.run()` returns). `MiningSimulation` coordinates trucks and stations in a single pass, matching existing state accounting logic.

#### 2. Non-Deterministic Priority Queue Tie-Breaking
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 119–126 (`sim_engine/event.py`), Lines 149–152 (`SimulationEngine.schedule`)
* **Discrepancy Description:**
  `Event` defines `@dataclass(order=True)` with only `time` participating in comparisons (`compare=False` on `action`, `event_type`, and `description`). When two events share identical timestamps ($t_1 == t_2$), Python's binary min-heap (`heapq`) does not guarantee FIFO order. Tie-breaking depends on index positions during sift-up and sift-down operations, causing non-deterministic execution order for simultaneous events and breaking regression test determinism.
* **Recommendation:**
  Add an auto-incrementing monotonic sequence counter (`_seq: int`) to `SimulationEngine` and include `seq: int` in `Event` as a secondary comparison key: `Event(time: float, seq: int, action: Callable, ...)`.

---

### Major Findings (🟡 Significant Structural & Architectural Issues)

#### 3. Breaking API Contract for `Reporter` and Legacy Adapter
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 189–191, 199–203
* **Discrepancy Description:**
  The draft changes `Reporter.__init__` to accept `(trucks, stations, duration_hours)` instead of `SimulationEngine`. Existing tests explicitly instantiate `Reporter(engine)`. Furthermore, existing tests mutate `engine.rng = StubRandom(...)` prior to running, which will not affect scenario random draws if the legacy adapter does not explicitly forward property assignments.
* **Recommendation:**
  Support polymorphic initialization in `Reporter` (`Reporter(engine)` and `Reporter(trucks=..., stations=..., duration_hours=...)`). Ensure the legacy adapter implements descriptor/property forwarding for `rng`.

#### 4. Lack of Virtual Time Monotonicity, Past-Time Guards, and Peeking Semantics
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 149–162 (`sim_engine/engine.py`), Lines 208–221
* **Discrepancy Description:**
  `schedule(time, action)` does not assert `time >= self.clock`, allowing past-time scheduling that violates causality. In addition, popping an event before verifying `event.time > until` drops future events from the queue unless pushed back.
* **Recommendation:**
  Add a causality check (`if time < self.clock: raise ValueError(...)`) and use queue peeking (`self._queue[0].time > until`) rather than popping and discarding future events.

#### 5. Missing Trade-Off Evaluation Table in Alternatives Considered
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 225–251
* **Discrepancy Description:**
  Under `feature-spec-standard`, architectural alternatives must be summarized in a comparison matrix evaluating options across standard criteria (e.g., Coupling, Overhead, Project Constraints, Decision) before detailed prose.
* **Recommendation:**
  Insert a markdown comparison table summarizing Alternatives A through D above the detailed subsections.

#### 6. Missing Explicit `## Open Questions` / `## Unresolved Issues` Section
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Section hierarchy (post line 250)
* **Discrepancy Description:**
  The original `## Open Questions` section was replaced by `## Resolved Decisions`. The specification standard requires an explicit `## Open Questions` section (stating "None" if all are resolved) to certify that no unresolved questions remain.
* **Recommendation:**
  Add `## Open Questions` stating "None (all architectural questions resolved during brainstorming)".

#### 7. Section Hierarchy and Placement of `## Resolved Decisions`
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 56–62
* **Discrepancy Description:**
  `## Resolved Decisions` is placed before CUJs and Technical Architecture, disrupting the logical flow from requirements to design.
* **Recommendation:**
  Move `## Resolved Decisions` to follow `## Alternatives Considered`.

#### 8. Sub-Section Structural Asymmetry in Component Details
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 110–204
* **Discrepancy Description:**
  Subsection 1 (`sim_engine`) includes narrative bullets and code snippets; Subsection 2 (`mining`) uses deeply nested bullets with no code snippets; Subsection 3 (`main.py`) has no module breakdown, jumping straight to code.
* **Recommendation:**
  Standardize subsections to follow a uniform layout (Responsibilities, Component Breakdown, API Schema).

#### 9. Colloquial Phrasing and Promotional Adjectives
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 28, 30, 58–59
* **Discrepancy Description:**
  * Line 28: "or shoehorning unrelated models" is informal.
  * Line 30: "clean, custom object-oriented simulation kernel" uses subjective fluff ("clean").
  * Line 58: "reconcile mid-flight activities" uses a mixed metaphor for lunar surface trucks.
  * Line 59: "fully deterministic and reproducible" contains synonym bloat.
* **Recommendation:**
  Replace with objective technical terms: "integrating unrelated domain models", "standalone discrete-event kernel", "in-progress activities", and "deterministic execution".

---

### Nits (🟢 Minor Improvements)

#### 10. Lack of Event Cancellation Primitive in Core Kernel
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 119–126, 149–152
* **Recommendation:**
  Return an `EventHandle` from `schedule()` containing `cancel()` and `is_cancelled: bool` to support extensible descheduling.

#### 11. Redundant Metadata Fields on `Event`
* **Reviewer Lens:** `egm-design`, `egm-style`
* **Affected Scope:** Lines 123–126
* **Recommendation:**
  Replace `event_type: Any` and `description: str` with a single `label: str = ""` field.

#### 12. List Bullet Style and Markdown Thematic Breaks
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 7, 17, 32, 44, 179–183, 209–220
* **Recommendation:**
  Standardize on `---` for thematic breaks and uniform 1-space indentation (`* **`) with asterisks across all bullet lists.

#### 13. Missing Relative File Hyperlinks
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 21, 30, 49, 230
* **Recommendation:**
  Convert plain text file references (`instructions.md`, `simulation/engine.py`, etc.) into clickable relative Markdown links.
