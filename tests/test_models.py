"""Tests for SimConfig and the data models (Event, MiningTruck, UnloadStation)."""

import dataclasses
import heapq
import unittest

from simulation import Event, EventType, MiningTruck, SimConfig, TruckState, UnloadStation


class TestSimConfig(unittest.TestCase):
    def test_defaults_match_required_scenario(self):
        config = SimConfig()
        self.assertEqual(config.num_trucks, 10)
        self.assertEqual(config.num_stations, 3)
        self.assertEqual(config.duration_hours, 72)
        self.assertIsNone(config.random_seed)

    def test_duration_minutes(self):
        self.assertEqual(SimConfig(duration_hours=72).duration_minutes, 4320)
        self.assertEqual(SimConfig(duration_hours=1).duration_minutes, 60)

    def test_is_immutable(self):
        config = SimConfig()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            config.num_trucks = 5

    def test_rejects_non_positive_values(self):
        for kwargs in (
            {"num_trucks": 0},
            {"num_stations": 0},
            {"duration_hours": 0},
            {"num_trucks": -1},
            {"num_stations": -3},
            {"duration_hours": -72},
        ):
            with self.subTest(**kwargs):
                with self.assertRaises(ValueError):
                    SimConfig(**kwargs)

    def test_error_names_the_invalid_field(self):
        with self.assertRaisesRegex(ValueError, "num_stations must be at least 1"):
            SimConfig(num_stations=0)

    def test_accepts_minimum_values(self):
        config = SimConfig(num_trucks=1, num_stations=1, duration_hours=1)
        self.assertEqual(config.duration_minutes, 60)


class TestEvent(unittest.TestCase):
    def test_events_order_by_time(self):
        early = Event(time=10.0, type=EventType.ARRIVE_MINE, truck_id=5)
        late = Event(time=20.0, type=EventType.MINING_COMPLETE, truck_id=0)
        self.assertLess(early, late)

    def test_only_time_participates_in_comparison(self):
        a = Event(time=10.0, type=EventType.ARRIVE_MINE, truck_id=1)
        b = Event(time=10.0, type=EventType.FINISH_UNLOAD, truck_id=2, station_id=0)
        self.assertFalse(a < b)
        self.assertFalse(b < a)

    def test_heap_pops_events_chronologically(self):
        times = [300.0, 60.0, 150.0, 90.0, 60.0, 240.0]
        heap: list[Event] = []
        for i, t in enumerate(times):
            heapq.heappush(heap, Event(time=t, type=EventType.ARRIVE_MINE, truck_id=i))
        popped = [heapq.heappop(heap).time for _ in range(len(times))]
        self.assertEqual(popped, sorted(times))

    def test_station_id_defaults_to_none(self):
        event = Event(time=0.0, type=EventType.MINING_COMPLETE, truck_id=0)
        self.assertIsNone(event.station_id)

    def test_repr_is_readable(self):
        event = Event(time=90.0, type=EventType.START_UNLOAD, truck_id=3, station_id=1)
        self.assertEqual(repr(event), "Event(t=90.0, START_UNLOAD, truck=3, station=1)")


class TestEntities(unittest.TestCase):
    def test_truck_starts_with_zeroed_stats(self):
        truck = MiningTruck(id=7)
        self.assertEqual(truck.loads_delivered, 0)
        self.assertEqual(truck.time_mining, 0.0)
        self.assertEqual(truck.time_traveling, 0.0)
        self.assertEqual(truck.time_waiting, 0.0)
        self.assertEqual(truck.time_unloading, 0.0)

    def test_truck_starts_mining(self):
        self.assertIs(MiningTruck(id=0)._state, TruckState.MINING)

    def test_station_starts_free_with_zeroed_stats(self):
        station = UnloadStation(id=2)
        self.assertEqual(station.available_at, 0.0)
        self.assertEqual(station.trucks_served, 0)
        self.assertEqual(station.time_busy, 0.0)


if __name__ == "__main__":
    unittest.main()
