"""Tests for Reporter: metric calculations and Markdown output."""

import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout

from simulation import Reporter, SimConfig, SimulationEngine


def engine_with_known_stats() -> SimulationEngine:
    """A 10-hour (600 min) engine with hand-set statistics; never run."""
    engine = SimulationEngine(SimConfig(num_trucks=2, num_stations=1, duration_hours=10))

    t0, t1 = engine.trucks
    t0.loads_delivered = 3
    t0.time_mining, t0.time_traveling = 300, 120
    t0.time_waiting, t0.time_unloading = 30, 60

    t1.loads_delivered = 1
    t1.time_mining, t1.time_traveling = 150, 60
    t1.time_waiting, t1.time_unloading = 0, 30

    station = engine.stations[0]
    station.trucks_served = 4
    station.time_busy = 90
    return engine


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.reporter = Reporter(engine_with_known_stats())

    def test_total_loads(self):
        self.assertEqual(self.reporter.total_loads_delivered, 4)

    def test_throughput_per_hour(self):
        self.assertAlmostEqual(self.reporter.system_throughput_loads_per_hour, 0.4)

    def test_truck_utilization_excludes_waiting(self):
        # (300 + 120 + 60) / 600 and (150 + 60 + 30) / 600
        self.assertAlmostEqual(self.reporter.truck_utilization(0), 80.0)
        self.assertAlmostEqual(self.reporter.truck_utilization(1), 40.0)

    def test_average_truck_utilization(self):
        self.assertAlmostEqual(self.reporter.average_truck_utilization, 60.0)

    def test_station_utilization(self):
        self.assertAlmostEqual(self.reporter.station_utilization(0), 15.0)
        self.assertAlmostEqual(self.reporter.average_station_utilization, 15.0)


class TestMarkdown(unittest.TestCase):
    def setUp(self):
        self.reporter = Reporter(engine_with_known_stats())
        self.markdown = self.reporter.generate_markdown()

    def test_summary_lists_configuration(self):
        self.assertIn("**Mining Trucks (n):** 2", self.markdown)
        self.assertIn("**Unload Stations (m):** 1", self.markdown)
        self.assertIn("**Simulation Duration:** 10 hours (600 minutes)", self.markdown)
        self.assertIn("None (Non-deterministic)", self.markdown)

    def test_summary_lists_totals(self):
        self.assertIn("**Total Loads Delivered:** 4", self.markdown)
        self.assertIn("**System Throughput:** 0.40 loads/hr", self.markdown)
        self.assertIn("**Average Truck Utilization:** 60.00%", self.markdown)
        self.assertIn("**Average Station Utilization:** 15.00%", self.markdown)

    def test_truck_rows_in_hours(self):
        self.assertIn("| Truck 0 | 3 | 5.00 | 2.00 | 0.50 | 1.00 | 80.00% |", self.markdown)
        self.assertIn("| Truck 1 | 1 | 2.50 | 1.00 | 0.00 | 0.50 | 40.00% |", self.markdown)

    def test_station_row_includes_idle_time(self):
        self.assertIn("| Station 0 | 4 | 1.50 | 8.50 | 15.00% |", self.markdown)

    def test_seed_is_reported_when_set(self):
        engine = SimulationEngine(SimConfig(random_seed=42, duration_hours=1))
        self.assertIn("**Random Seed:** 42", Reporter(engine).generate_markdown())

    def test_one_row_per_entity(self):
        engine = SimulationEngine(SimConfig(num_trucks=10, num_stations=3, random_seed=0))
        engine.run()
        markdown = Reporter(engine).generate_markdown()
        self.assertEqual(len(re.findall(r"^\| Truck \d+ \|", markdown, re.M)), 10)
        self.assertEqual(len(re.findall(r"^\| Station \d+ \|", markdown, re.M)), 3)


class TestOutput(unittest.TestCase):
    def setUp(self):
        self.reporter = Reporter(engine_with_known_stats())

    def test_print_report_writes_markdown_to_stdout(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.reporter.print_report()
        self.assertEqual(buffer.getvalue().rstrip("\n"), self.reporter.generate_markdown().rstrip("\n"))

    def test_save_markdown_creates_missing_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "dir", "report.md")
            self.reporter.save_markdown(path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), self.reporter.generate_markdown())

    def test_save_markdown_logs_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.md")
            with self.assertLogs("simulation.reporting", level="INFO") as logs:
                self.reporter.save_markdown(path)
        self.assertEqual(logs.output, [f"INFO:simulation.reporting:Saved report to {path}"])

    def test_save_markdown_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("old contents")
            self.reporter.save_markdown(path)
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("old contents", f.read())


if __name__ == "__main__":
    unittest.main()
