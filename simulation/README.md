# `simulation` package (backward-compatibility facade)

> **Note:** This package is a backward-compatibility facade. All domain logic now lives in
> [`sim_engine/`](../sim_engine/README.md) (the reusable discrete-event engine) and
> [`mining/`](../mining/README.md) (the lunar mining domain).

The `simulation` package re-exports all public symbols from `sim_engine` and `mining`
under their original import paths. Existing scripts, tests, and benchmarks that import
from `simulation` continue to work unchanged.

| Module | Wraps |
|---|---|
| `simulation.config` | `mining.config` |
| `simulation.models` | `mining.models` (plus legacy `Event` and `EventType` aliases) |
| `simulation.engine` | `sim_engine.SimulationEngine` + `mining.MiningSimulation` |
| `simulation.reporting` | `mining.reporting` |

For new code, import directly from `sim_engine` and `mining`.
