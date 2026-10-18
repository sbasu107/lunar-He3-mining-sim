"""Reporting and statistics generation for the lunar He-3 mining simulation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .config import HOURS_TO_MINUTES

if TYPE_CHECKING:
    from .engine import SimulationEngine


class Reporter:
    """Calculates and formats performance and efficiency statistics.

    Provides formatted text summaries for the console as well as comprehensive
    Markdown reports suitable for saving to file.

    Attributes:
        engine: The completed SimulationEngine instance.
        config: Simulation configuration parameters.
    """

    def __init__(self, engine: SimulationEngine) -> None:
        self.engine = engine
        self.config = engine.config

    # ------------------------------------------------------------------
    # Metric Calculations
    # ------------------------------------------------------------------

    @property
    def total_loads_delivered(self) -> int:
        """Total number of loads delivered by all trucks combined."""
        return sum(truck.loads_delivered for truck in self.engine.trucks)

    @property
    def system_throughput_loads_per_hour(self) -> float:
        """System-wide throughput measured in loads delivered per hour."""
        if self.config.duration_hours <= 0:
            return 0.0
        return self.total_loads_delivered / self.config.duration_hours

    def truck_utilization(self, truck_id: int) -> float:
        """Calculate active utilization percentage for a single truck.

        Active time consists of mining, traveling, and unloading. Waiting time
        is treated as non-productive idle queue delay.
        """
        truck = self.engine.trucks[truck_id]
        if self.config.duration_minutes <= 0:
            return 0.0
        active_minutes = (
            truck.time_mining + truck.time_traveling + truck.time_unloading
        )
        return (active_minutes / self.config.duration_minutes) * 100.0

    @property
    def average_truck_utilization(self) -> float:
        """Average active utilization across all trucks."""
        if not self.engine.trucks:
            return 0.0
        total_util = sum(
            self.truck_utilization(t.id) for t in self.engine.trucks
        )
        return total_util / len(self.engine.trucks)

    def station_utilization(self, station_id: int) -> float:
        """Calculate utilization percentage for a single unload station."""
        station = self.engine.stations[station_id]
        if self.config.duration_minutes <= 0:
            return 0.0
        return (station.time_busy / self.config.duration_minutes) * 100.0

    @property
    def average_station_utilization(self) -> float:
        """Average utilization across all unload stations."""
        if not self.engine.stations:
            return 0.0
        total_util = sum(
            self.station_utilization(s.id) for s in self.engine.stations
        )
        return total_util / len(self.engine.stations)

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_markdown(self) -> str:
        """Generate a complete Markdown-formatted summary report."""
        duration_hrs = self.config.duration_hours
        duration_mins = self.config.duration_minutes

        lines: list[str] = [
            "# Lunar Helium-3 Mining Simulation — Summary Report",
            "",
            "## Executive Summary",
            "",
            f"- **Simulation Duration:** {duration_hrs} hours ({duration_mins:.0f} minutes)",
            f"- **Mining Trucks (n):** {self.config.num_trucks}",
            f"- **Unload Stations (m):** {self.config.num_stations}",
            f"- **Random Seed:** {self.config.random_seed if self.config.random_seed is not None else 'None (Non-deterministic)'}",
            f"- **Total Loads Delivered:** {self.total_loads_delivered}",
            f"- **System Throughput:** {self.system_throughput_loads_per_hour:.2f} loads/hr",
            f"- **Average Truck Utilization:** {self.average_truck_utilization:.2f}%",
            f"- **Average Station Utilization:** {self.average_station_utilization:.2f}%",
            "",
            "---",
            "",
            "## Mining Trucks Performance",
            "",
            "| Truck ID | Loads Delivered | Mining Time (h) | Travel Time (h) | Wait Time (h) | Unload Time (h) | Utilization (%) |",
            "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for truck in self.engine.trucks:
            mining_h = truck.time_mining / HOURS_TO_MINUTES
            travel_h = truck.time_traveling / HOURS_TO_MINUTES
            wait_h = truck.time_waiting / HOURS_TO_MINUTES
            unload_h = truck.time_unloading / HOURS_TO_MINUTES
            util = self.truck_utilization(truck.id)

            lines.append(
                f"| Truck {truck.id} | {truck.loads_delivered} | "
                f"{mining_h:.2f} | {travel_h:.2f} | {wait_h:.2f} | {unload_h:.2f} | {util:.2f}% |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Unload Stations Performance",
            "",
            "| Station ID | Trucks Served | Busy Time (h) | Idle Time (h) | Utilization (%) |",
            "|:---:|:---:|:---:|:---:|:---:|",
        ])

        for station in self.engine.stations:
            busy_h = station.time_busy / HOURS_TO_MINUTES
            idle_h = max(0.0, (duration_mins - station.time_busy) / HOURS_TO_MINUTES)
            util = self.station_utilization(station.id)

            lines.append(
                f"| Station {station.id} | {station.trucks_served} | "
                f"{busy_h:.2f} | {idle_h:.2f} | {util:.2f}% |"
            )

        lines.append("")
        return "\n".join(lines)

    def print_report(self) -> None:
        """Print the formatted simulation report to standard output."""
        print(self.generate_markdown())

    def save_markdown(self, path: str) -> None:
        """Save the formatted markdown report to a file.

        Creates any missing parent directories automatically.

        Args:
            path: Destination file path (e.g. 'results/summary_report.md').
        """
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_markdown())
