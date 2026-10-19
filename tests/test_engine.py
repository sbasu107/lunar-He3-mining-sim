"""Tests for SimulationEngine.

Scenario tests replace the engine's RNG with ``StubRandom`` so every duration
is known and results can be checked against hand calculations. Property tests
run the real RNG across many seeds and sizes and check rules that must hold
for any run.
"""

import copy
import random
import unittest

from simulation import SimConfig, SimulationEngine, TruckState
from simulation.config import (
    MAX_MINING_HOURS,
    MAX_UNLOAD_MINUTES,
    MIN_MINING_HOURS,
    MIN_UNLOAD_MINUTES,
    TRAVEL_TIME_MINUTES,
)


class StubRandom:
    """Deterministic stand-in for ``random.Random``.

    Each argument is either a fixed value or a list consumed in draw order.
    """

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


class RecordingRandom(random.Random):
    """Real RNG that records every ``randint`` call for inspection."""

    def __init__(self, seed):
        super().__init__(seed)
        self.calls: list[tuple[int, int, int]] = []

    def randint(self, a, b):
        result = super().randint(a, b)
        self.calls.append((a, b, result))
        return result


def stub_engine(trucks, stations, hours, **stub_kwargs) -> SimulationEngine:
    engine = SimulationEngine(SimConfig(
        num_trucks=trucks, num_stations=stations, duration_hours=hours,
    ))
    engine.rng = StubRandom(**stub_kwargs)
    return engine


def total_truck_time(truck) -> float:
    return (truck.time_mining + truck.time_traveling
            + truck.time_waiting + truck.time_unloading)


# Sizes and seeds used by the property tests.
CONFIGS = [(1, 1), (10, 3), (5, 5), (20, 2), (3, 10), (50, 1)]
SEEDS = range(5)


def seeded_runs(hours=72):
    for trucks, stations in CONFIGS:
        for seed in SEEDS:
            engine = SimulationEngine(SimConfig(
                num_trucks=trucks, num_stations=stations,
                duration_hours=hours, random_seed=seed,
            ))
            engine.run()
            yield (trucks, stations, seed), engine


# ---------------------------------------------------------------------------
# Hand-calculated scenarios
# ---------------------------------------------------------------------------
class TestSingleTruckScenarios(unittest.TestCase):
    """1 h mining + 30 min travel + 30 min unload + 30 min travel = 150 min cycle."""

    def test_one_full_cycle(self):
        # 0-60 mine, 60-90 travel, 90-120 unload, 120-150 travel, 150- mine
        engine = stub_engine(1, 1, hours=3)
        engine.run()
        truck, station = engine.trucks[0], engine.stations[0]

        self.assertEqual(truck.loads_delivered, 1)
        self.assertEqual(truck.time_traveling, 2 * TRAVEL_TIME_MINUTES)
        self.assertEqual(truck.time_waiting, 0)
        self.assertEqual(truck.time_unloading, 30)
        self.assertEqual(station.trucks_served, 1)
        self.assertEqual(station.time_busy, 30)

    def test_two_cycles_ending_on_cycle_boundary(self):
        # The second cycle finishes exactly at t = 300 = the configured duration.
        engine = stub_engine(1, 1, hours=5)
        engine.run()
        truck = engine.trucks[0]

        self.assertEqual(truck.loads_delivered, 2)
        self.assertEqual(truck.time_mining, 120)
        self.assertEqual(truck.time_traveling, 120)
        self.assertEqual(truck.time_unloading, 60)
        self.assertEqual(total_truck_time(truck), 300)

    def test_event_exactly_at_end_time_is_processed(self):
        # Unload finishes at t = 120 with a 2 h duration: the load counts.
        engine = stub_engine(1, 1, hours=2)
        engine.run()
        self.assertEqual(engine.trucks[0].loads_delivered, 1)
        self.assertEqual(engine.clock, 120)

    def test_no_loads_when_duration_shorter_than_first_delivery(self):
        engine = stub_engine(1, 1, hours=2, mining_hours=5)
        engine.run()
        self.assertEqual(engine.trucks[0].loads_delivered, 0)
        self.assertEqual(engine.stations[0].trucks_served, 0)

    def test_variable_mining_durations_are_used(self):
        # Mining 2 h then 1 h: deliveries finish at 180 and 330.
        engine = stub_engine(1, 1, hours=6, mining_hours=[2, 1, 5])
        engine.run()
        self.assertEqual(engine.trucks[0].loads_delivered, 2)
        self.assertEqual(engine.trucks[0].time_mining, 180)


class TestQueueing(unittest.TestCase):
    def test_second_truck_waits_for_single_station(self):
        # Both trucks reach the station at t = 90. One unloads 90-120,
        # the other waits 30 min and unloads 120-150.
        engine = stub_engine(2, 1, hours=3)
        engine.run()

        waits = sorted(t.time_waiting for t in engine.trucks)
        self.assertEqual(waits, [0, 30])
        self.assertEqual(engine.stations[0].trucks_served, 2)
        self.assertEqual(engine.stations[0].time_busy, 60)

    def test_free_station_is_used_instead_of_queueing(self):
        engine = stub_engine(2, 2, hours=3)
        engine.run()

        self.assertEqual([t.time_waiting for t in engine.trucks], [0, 0])
        self.assertEqual([s.trucks_served for s in engine.stations], [1, 1])

    def test_truck_joins_queue_with_shortest_wait(self):
        # Three trucks arrive at t = 90. The first takes station 0 for 60 min
        # (free at 150), the second takes station 1 for 30 min (free at 120).
        # The third must queue at station 1, the shorter wait.
        engine = stub_engine(3, 2, hours=3, unload_minutes=[60, 30, 30])
        engine.run()

        self.assertEqual([s.trucks_served for s in engine.stations], [1, 2])
        self.assertEqual(sorted(t.time_waiting for t in engine.trucks), [0, 0, 30])

    def test_ties_go_to_lowest_station_id(self):
        engine = stub_engine(1, 3, hours=3)
        engine.run()
        self.assertEqual([s.trucks_served for s in engine.stations], [1, 0, 0])

    def test_queue_wait_accounts_for_every_truck_already_committed(self):
        # Four trucks arrive together at one station with 30 min unloads:
        # waits are 0, 30, 60, 90.
        engine = stub_engine(4, 1, hours=4)
        engine.run()
        self.assertEqual(sorted(t.time_waiting for t in engine.trucks), [0, 30, 60, 90])


class TestEndOfRunAccounting(unittest.TestCase):
    """Activities still in progress when the run ends are credited up to the end."""

    def test_mining_in_progress_at_end_is_counted(self):
        # Truck is mining from t = 150 when the run ends at 180.
        engine = stub_engine(1, 1, hours=3)
        engine.run()
        self.assertEqual(engine.trucks[0].time_mining, 90)

    def test_unload_in_progress_at_end_counts_toward_station_busy_time(self):
        # Unload runs 90-150 but the simulation ends at 120.
        engine = stub_engine(1, 1, hours=2, unload_minutes=60)
        engine.run()
        self.assertEqual(engine.stations[0].time_busy, 30)
        self.assertEqual(engine.trucks[0].time_unloading, 30)

    def test_waiting_in_progress_at_end_is_counted(self):
        # Second truck queues from t = 90; the run ends at 120.
        engine = stub_engine(2, 1, hours=2, unload_minutes=60)
        engine.run()
        self.assertEqual(sum(t.time_waiting for t in engine.trucks), 30)

    def test_travel_in_progress_at_end_is_counted(self):
        # 0-60 mine, 60-90 travel, 90-135 unload, 135-165 travel,
        # 165-225 mine, 225-255 travel: the run ends at 240, mid-travel.
        engine = stub_engine(1, 1, hours=4, unload_minutes=45)
        engine.run()
        self.assertEqual(engine.trucks[0].time_traveling, 75)

    def test_truck_state_times_sum_to_duration(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    self.assertAlmostEqual(
                        total_truck_time(truck), engine.config.duration_minutes,
                        msg=f"truck={truck.id}",
                    )

    def test_clock_ends_at_duration(self):
        engine = stub_engine(1, 1, hours=3)
        engine.run()
        self.assertEqual(engine.clock, 180)


class TestRunOnce(unittest.TestCase):
    def test_second_run_raises(self):
        engine = SimulationEngine(SimConfig(random_seed=1))
        engine.run()
        with self.assertRaises(RuntimeError):
            engine.run()

    def test_second_run_leaves_results_untouched(self):
        engine = SimulationEngine(SimConfig(random_seed=1))
        engine.run()
        trucks, stations = copy.deepcopy(engine.trucks), copy.deepcopy(engine.stations)
        with self.assertRaises(RuntimeError):
            engine.run()
        self.assertEqual(engine.trucks, trucks)
        self.assertEqual(engine.stations, stations)


# ---------------------------------------------------------------------------
# Properties that must hold for any seed and configuration
# ---------------------------------------------------------------------------
class TestInvariants(unittest.TestCase):
    def test_entity_counts_match_config(self):
        for (trucks, stations, _), engine in seeded_runs():
            self.assertEqual(len(engine.trucks), trucks)
            self.assertEqual(len(engine.stations), stations)

    def test_no_negative_times(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    for value in (truck.time_mining, truck.time_traveling,
                                  truck.time_waiting, truck.time_unloading):
                        self.assertGreaterEqual(value, 0)
                for station in engine.stations:
                    self.assertGreaterEqual(station.time_busy, 0)

    def test_truck_time_never_exceeds_duration(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    self.assertLessEqual(
                        total_truck_time(truck), engine.config.duration_minutes
                    )

    def test_station_busy_time_never_exceeds_duration(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for station in engine.stations:
                    self.assertLessEqual(station.time_busy, engine.config.duration_minutes)

    def test_loads_delivered_equals_trucks_served(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                self.assertEqual(
                    sum(t.loads_delivered for t in engine.trucks),
                    sum(s.trucks_served for s in engine.stations),
                )

    def test_truck_unload_time_equals_station_busy_time(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                self.assertAlmostEqual(
                    sum(t.time_unloading for t in engine.trucks),
                    sum(s.time_busy for s in engine.stations),
                )

    def test_unload_time_per_load_within_bounds(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    loads = truck.loads_delivered
                    # A truck cut off mid-unload has one partial unload on top.
                    partial = MAX_UNLOAD_MINUTES if truck._state is TruckState.UNLOADING else 0
                    self.assertGreaterEqual(truck.time_unloading, loads * MIN_UNLOAD_MINUTES)
                    self.assertLessEqual(truck.time_unloading, loads * MAX_UNLOAD_MINUTES + partial)

    def test_loads_bounded_by_fastest_possible_cycle(self):
        # Fastest first delivery: 60 + 30 + 30 = 120 min, then every 150 min.
        duration = 72 * 60
        max_loads = (duration - 120) // 150 + 1
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    self.assertLessEqual(truck.loads_delivered, max_loads)

    def test_no_waiting_when_stations_outnumber_trucks(self):
        for key, engine in seeded_runs():
            trucks, stations, _ = key
            if stations < trucks:
                continue
            with self.subTest(config=key):
                for truck in engine.trucks:
                    self.assertEqual(truck.time_waiting, 0)

    def test_clock_never_passes_duration(self):
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                self.assertLessEqual(engine.clock, engine.config.duration_minutes)

    def test_completed_mining_time_is_whole_hours(self):
        # Mining durations have 1-hour resolution; only a session cut off by
        # the end of the run can be a partial hour.
        for key, engine in seeded_runs():
            with self.subTest(config=key):
                for truck in engine.trucks:
                    if truck._state is not TruckState.MINING:
                        self.assertEqual(truck.time_mining % 60, 0)

    def test_random_draws_stay_within_spec(self):
        engine = SimulationEngine(SimConfig(num_trucks=20, num_stations=3, random_seed=7))
        engine.rng = RecordingRandom(7)
        engine.run()

        self.assertTrue(engine.rng.calls)
        allowed = {
            (MIN_MINING_HOURS, MAX_MINING_HOURS),
            (MIN_UNLOAD_MINUTES, MAX_UNLOAD_MINUTES),
        }
        for a, b, result in engine.rng.calls:
            self.assertIn((a, b), allowed)
            self.assertTrue(a <= result <= b)

    def test_one_initial_mining_draw_per_truck(self):
        engine = SimulationEngine(SimConfig(num_trucks=8, duration_hours=1))
        engine.rng = RecordingRandom(0)
        engine.run()
        mining_draws = [c for c in engine.rng.calls
                        if (c[0], c[1]) == (MIN_MINING_HOURS, MAX_MINING_HOURS)]
        self.assertEqual(len(mining_draws), 8)


class TestEdgeCases(unittest.TestCase):
    def test_one_hour_run_delivers_nothing(self):
        engine = SimulationEngine(SimConfig(num_trucks=10, num_stations=3,
                                            duration_hours=1, random_seed=0))
        engine.run()
        self.assertEqual(sum(t.loads_delivered for t in engine.trucks), 0)

    def test_overloaded_single_station_is_nearly_always_busy(self):
        engine = SimulationEngine(SimConfig(num_trucks=50, num_stations=1, random_seed=0))
        engine.run()
        utilization = engine.stations[0].time_busy / engine.config.duration_minutes
        self.assertGreater(utilization, 0.9)

    def test_overloaded_station_makes_trucks_wait(self):
        engine = SimulationEngine(SimConfig(num_trucks=50, num_stations=1, random_seed=0))
        engine.run()
        self.assertGreater(sum(t.time_waiting for t in engine.trucks), 0)

    def test_more_stations_does_not_reduce_throughput(self):
        # Sanity check on scaling: 10 trucks with 10 stations should deliver
        # at least as much as with 1 station (same seed).
        loads = {}
        for stations in (1, 10):
            engine = SimulationEngine(SimConfig(num_trucks=10, num_stations=stations,
                                                random_seed=3))
            engine.run()
            loads[stations] = sum(t.loads_delivered for t in engine.trucks)
        self.assertGreaterEqual(loads[10], loads[1])

    def test_long_run_completes(self):
        engine = SimulationEngine(SimConfig(num_trucks=100, num_stations=10,
                                            duration_hours=24 * 30, random_seed=0))
        engine.run()
        self.assertGreater(sum(t.loads_delivered for t in engine.trucks), 0)


class TestReproducibility(unittest.TestCase):
    @staticmethod
    def _run(seed):
        engine = SimulationEngine(SimConfig(random_seed=seed))
        engine.run()
        return engine

    def test_same_seed_gives_identical_results(self):
        a, b = self._run(42), self._run(42)
        self.assertEqual(a.trucks, b.trucks)
        self.assertEqual(a.stations, b.stations)

    def test_different_seeds_give_different_results(self):
        a, b = self._run(1), self._run(2)
        self.assertNotEqual(a.trucks, b.trucks)

    def test_engine_does_not_touch_global_random_state(self):
        random.seed(123)
        expected = random.random()
        random.seed(123)
        self._run(42)
        self.assertEqual(random.random(), expected)


if __name__ == "__main__":
    unittest.main()
