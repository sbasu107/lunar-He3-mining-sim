# `mining` package

The lunar Helium-3 mining domain implementation, encapsulating mining business logic, operational state machines, entity metrics, and reporting.

## Overview

The `mining` package implements the operational model of Helium-3 mining operations on the Moon using `sim_engine` as its underlying discrete-event scheduler:

- **Mining Trucks**: Cycle through states `MINING -> TRAVELING -> WAITING -> UNLOADING -> TRAVELING -> MINING`.
- **Unload Stations**: Serve trucks using an optimistic shortest-wait heuristic based on each station's `available_at` timestamp.
- **Reporting**: Computes throughput, utilization, and comprehensive Markdown reports.

## Architecture

| Module | Purpose |
|---|---|
| [`config.py`](config.py) | Timing constants and the `SimConfig` dataclass |
| [`models.py`](models.py) | Domain models: `TruckState`, `MiningEventType`, `MiningTruck`, `UnloadStation` |
| [`scenario.py`](scenario.py) | `MiningSimulation` domain coordinator wiring entities with `sim_engine.SimulationEngine` |
| [`reporting.py`](reporting.py) | `Reporter` generating statistics, metrics, and Markdown reports |

## Usage

```python
from sim_engine import SimulationEngine
from mining import MiningSimulation, SimConfig, Reporter

config = SimConfig(num_trucks=10, num_stations=3, duration_hours=72, random_seed=42)
engine = SimulationEngine()
scenario = MiningSimulation(engine, config)

scenario.setup()
engine.run(until=config.duration_minutes)
scenario.finalize(until=config.duration_minutes)

reporter = Reporter(trucks=scenario.trucks, stations=scenario.stations, config=config, seed=scenario.seed)
reporter.print_report()
```
