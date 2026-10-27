"""Unit tests for the domain-agnostic sim_engine package."""

import unittest

from sim_engine import Event, EventHandle, SimulationEngine


class TestEventAndHandle(unittest.TestCase):
    def test_event_ordering_by_time_and_seq(self):
        handle = EventHandle()
        e1 = Event(time=10.0, seq=1, action=lambda: None, handle=handle, label="first")
        e2 = Event(time=10.0, seq=2, action=lambda: None, handle=handle, label="second")
        e3 = Event(time=5.0, seq=3, action=lambda: None, handle=handle, label="early")

        self.assertLess(e3, e1)
        self.assertLess(e1, e2)

    def test_event_repr(self):
        handle = EventHandle()
        event = Event(time=15.0, seq=4, action=lambda: None, handle=handle, label="test_event")
        self.assertIn("t=15.0", repr(event))
        self.assertIn("seq=4", repr(event))
        self.assertIn("'test_event'", repr(event))
        self.assertNotIn("CANCELLED", repr(event))

        handle.cancel()
        self.assertIn("CANCELLED", repr(event))

    def test_handle_cancellation(self):
        handle = EventHandle()
        self.assertFalse(handle.is_cancelled)
        handle.cancel()
        self.assertTrue(handle.is_cancelled)


class TestSimulationEngine(unittest.TestCase):
    def test_clock_advancement(self):
        engine = SimulationEngine()
        executed = []

        def record(val: int):
            executed.append((engine.clock, val))

        engine.schedule(10.0, lambda: record(1))
        engine.schedule(25.0, lambda: record(2))
        engine.run(until=30.0)

        self.assertEqual(executed, [(10.0, 1), (25.0, 2)])
        self.assertEqual(engine.clock, 30.0)

    def test_deterministic_fifo_tie_breaking(self):
        engine = SimulationEngine()
        order = []

        engine.schedule(10.0, lambda: order.append("A"), label="A")
        engine.schedule(10.0, lambda: order.append("B"), label="B")
        engine.schedule(10.0, lambda: order.append("C"), label="C")
        engine.run(until=15.0)

        self.assertEqual(order, ["A", "B", "C"])

    def test_event_cancellation(self):
        engine = SimulationEngine()
        executed = []

        engine.schedule(5.0, lambda: executed.append("A"))
        h_b = engine.schedule(10.0, lambda: executed.append("B"))
        engine.schedule(15.0, lambda: executed.append("C"))

        h_b.cancel()
        engine.run(until=20.0)

        self.assertEqual(executed, ["A", "C"])

    def test_run_until_cutoff(self):
        engine = SimulationEngine()
        executed = []

        engine.schedule(5.0, lambda: executed.append(1))
        engine.schedule(10.0, lambda: executed.append(2))
        engine.schedule(15.0, lambda: executed.append(3))

        engine.run(until=10.0)

        self.assertEqual(executed, [(1), (2)])
        self.assertEqual(engine.clock, 10.0)
        self.assertEqual(engine.pending_count, 1)

    def test_cannot_schedule_in_past(self):
        engine = SimulationEngine()
        engine.schedule(10.0, lambda: None)
        engine.run(until=10.0)

        with self.assertRaises(ValueError):
            engine.schedule(5.0, lambda: None)

    def test_run_can_only_be_called_once(self):
        engine = SimulationEngine()
        engine.run(until=10.0)

        with self.assertRaises(RuntimeError):
            engine.run(until=20.0)


if __name__ == "__main__":
    unittest.main()
