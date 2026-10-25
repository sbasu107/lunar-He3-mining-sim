"""Unit tests for the mining domain package."""

import unittest

from mining import (
    MiningSimulation,
    Reporter,
    SimConfig,
)
from mining.config import (
    MAX_MINING_HOURS,
    MAX_UNLOAD_MINUTES,
    MIN_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    TRAVEL_TIME_MINUTES,
)
from sim_engine import SimulationEngine


class StubRandom:
    """Deterministic stand-in for random.Random."""

    def __init__(self, mining_hours=1, unload_minutes=30):
        self._mining = mining_hours
        self._unload = unload_minutes

    @staticmethod
    def _next(source):
        return source.pop(0) if isinstance(source, list) else source

    def randint(self, a, b):
        if (a, b) == (MIN_MINING_HOURS, MAX_MINING_HOURS):
            return self._next(self._mining)
        if (a, b) == (MIN_UNLOAD_MINUTES, MAX_UNLOAD_MINUTES):
            return self._next(self._unload)
        raise AssertionError(f"unexpected randint({a}, {b})")


def run_mining_sim(
    trucks: int,
    stations: int,
    hours: int,
    use_stub: bool = True,
    **stub_kwargs,
) -> tuple[SimulationEngine, MiningSimulation]:
    config = SimConfig(num_trucks=trucks, num_stations=stations, duration_hours=hours)
    engine = SimulationEngine()
    scenario = MiningSimulation(engine, config)
    if use_stub:
        scenario.rng = StubRandom(**stub_kwargs)
    scenario.setup()
    engine.run(until=config.duration_minutes)
    scenario.finalize(until=config.duration_minutes)
    return engine, scenario


class TestMiningSimulation(unittest.TestCase):
    def test_single_truck_full_cycle(self):
        # 0-60 mine, 60-90 travel, 90-120 unload, 120-150 travel, 150-180 mine
        _, scenario = run_mining_sim(1, 1, hours=3)
        truck, station = scenario.trucks[0], scenario.stations[0]

        self.assertEqual(truck.loads_delivered, 1)
        self.assertEqual(truck.time_traveling, 2 * TRAVEL_TIME_MINUTES)
        self.assertEqual(truck.time_waiting, 0)
        self.assertEqual(truck.time_unloading, 30)
        self.assertEqual(station.trucks_served, 1)
        self.assertEqual(station.time_busy, 30)

    def test_queueing_shortest_wait(self):
        # 3 trucks, 2 stations. Station 0 takes 60 min, Station 1 takes 30 min.
        # Truck 3 must choose station 1.
        _, scenario = run_mining_sim(3, 2, hours=3, unload_minutes=[60, 30, 30])
        self.assertEqual([s.trucks_served for s in scenario.stations], [1, 2])
        self.assertEqual(sorted(t.time_waiting for t in scenario.trucks), [0, 0, 30])

    def test_truck_state_times_sum_to_duration(self):
        _, scenario = run_mining_sim(5, 2, hours=10, use_stub=False)
        total_duration = 10 * 60.0
        for truck in scenario.trucks:
            total_time = (
                truck.time_mining
                + truck.time_traveling
                + truck.time_waiting
                + truck.time_unloading
            )
            self.assertAlmostEqual(total_time, total_duration)

    def test_reporter_polymorphic_initialization(self):
        _, scenario = run_mining_sim(2, 1, hours=5, use_stub=False)

        # From scenario / target
        r1 = Reporter(scenario)
        self.assertEqual(r1.total_loads_delivered, sum(t.loads_delivered for t in scenario.trucks))

        # Explicit construction with config
        r2 = Reporter(
            trucks=scenario.trucks,
            stations=scenario.stations,
            config=scenario.config,
            seed=scenario.seed,
        )
        self.assertEqual(r2.total_loads_delivered, r1.total_loads_delivered)
        self.assertEqual(r2.generate_markdown(), r1.generate_markdown())


if __name__ == "__main__":
    unittest.main()
