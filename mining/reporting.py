"""Reporting and statistics generation for the lunar He-3 mining simulation."""

from __future__ import annotations

import logging
import os
from typing import Any

from .config import HOURS_TO_MINUTES
from .models import MiningTruck, UnloadStation

logger = logging.getLogger(__name__)


class Reporter:
    """Calculates and formats performance and efficiency statistics.

    Provides formatted text summaries for the console as well as comprehensive
    Markdown reports suitable for saving to file.

    Attributes:
        trucks:   List of mining trucks.
        stations: List of unload stations.
    """

    logger: logging.Logger = logger

    def __init__(
        self,
        target: Any = None,
        *,
        trucks: list[MiningTruck] | None = None,
        stations: list[UnloadStation] | None = None,
        duration_hours: int | None = None,
        seed: int | None = None,
        config: Any = None,
        random_seed_configured: bool | None = None,
    ) -> None:
        self.engine: Any = target
        if target is not None:
            self.trucks: list[MiningTruck] = target.trucks
            self.stations: list[UnloadStation] = target.stations
            self.config: Any = getattr(target, "config", config)
            if self.config is not None:
                self.duration_hours: int = self.config.duration_hours
                self.seed: int | None = getattr(target, "seed", self.config.random_seed)
                if random_seed_configured is not None:
                    self.random_seed_configured = random_seed_configured
                else:
                    self.random_seed_configured = self.config.random_seed is not None
            else:
                self.duration_hours = duration_hours if duration_hours is not None else 0
                self.seed = seed if seed is not None else getattr(target, "seed", None)
                if random_seed_configured is not None:
                    self.random_seed_configured = random_seed_configured
                else:
                    self.random_seed_configured = self.seed is not None
        else:
            self.trucks = trucks if trucks is not None else []
            self.stations = stations if stations is not None else []
            self.config = config
            if config is not None:
                self.duration_hours = config.duration_hours
                self.seed = seed if seed is not None else config.random_seed
                if random_seed_configured is not None:
                    self.random_seed_configured = random_seed_configured
                else:
                    self.random_seed_configured = config.random_seed is not None
            else:
                self.duration_hours = duration_hours if duration_hours is not None else 0
                self.seed = seed
                if random_seed_configured is not None:
                    self.random_seed_configured = random_seed_configured
                else:
                    self.random_seed_configured = self.seed is not None

    @property
    def duration_minutes(self) -> float:
        """Simulation duration converted to minutes."""
        return float(self.duration_hours * HOURS_TO_MINUTES)

    # ------------------------------------------------------------------
    # Metric Calculations
    # ------------------------------------------------------------------

    @property
    def total_loads_delivered(self) -> int:
        """Total number of loads delivered by all trucks combined."""
        return sum(truck.loads_delivered for truck in self.trucks)

    @property
    def system_throughput_loads_per_hour(self) -> float:
        """System-wide throughput measured in loads delivered per hour."""
        if self.duration_hours == 0:
            return 0.0
        return self.total_loads_delivered / self.duration_hours

    def truck_utilization(self, truck_id: int) -> float:
        """Calculate active utilization percentage for a single truck.

        Active time consists of mining, traveling, and unloading. Waiting time
        is treated as non-productive idle queue delay.
        """
        truck = self.trucks[truck_id]
        active_minutes = (
            truck.time_mining + truck.time_traveling + truck.time_unloading
        )
        return (active_minutes / self.duration_minutes) * 100.0

    @property
    def average_truck_utilization(self) -> float:
        """Average active utilization across all trucks."""
        if not self.trucks:
            return 0.0
        total_util = sum(
            self.truck_utilization(t.id) for t in self.trucks
        )
        return total_util / len(self.trucks)

    def station_utilization(self, station_id: int) -> float:
        """Calculate utilization percentage for a single unload station."""
        station = self.stations[station_id]
        return (station.time_busy / self.duration_minutes) * 100.0

    @property
    def average_station_utilization(self) -> float:
        """Average utilization across all unload stations."""
        if not self.stations:
            return 0.0
        total_util = sum(
            self.station_utilization(s.id) for s in self.stations
        )
        return total_util / len(self.stations)

    # ------------------------------------------------------------------
    # Report Generation
    # ------------------------------------------------------------------

    def generate_markdown(self) -> str:
        """Generate a complete Markdown-formatted summary report."""
        duration_hrs = self.duration_hours
        duration_mins = self.duration_minutes

        lines: list[str] = [
            "# Lunar Helium-3 Mining Simulation — Summary Report",
            "",
            "## Executive Summary",
            "",
            f"- **Simulation Duration:** {duration_hrs} hours ({duration_mins:.0f} minutes)",
            f"- **Mining Trucks (n):** {len(self.trucks)}",
            f"- **Unload Stations (m):** {len(self.stations)}",
            f"- **Random Seed:** {self.seed}"
            + ("" if self.random_seed_configured else " *(auto-generated — use `--seed` to reproduce)*"),
            f"- **Total Loads Delivered:** {self.total_loads_delivered}",
            f"- **System Throughput:** {self.system_throughput_loads_per_hour:.2f} loads/hr",
            f"- **Average Truck Utilization:** {self.average_truck_utilization:.2f}%",
            f"- **Average Station Utilization:** {self.average_station_utilization:.2f}%",
            "",
            "---",
            "",
            "## Mining Trucks Performance",
            "",
            "| Truck ID | Loads Delivered | Mining Time (h) | Travel Time (h) | Wait Time (h) | Unload Time (h) | Utilization (%) |",  # noqa: E501
            "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for truck in self.trucks:
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

        for station in self.stations:
            busy_h = station.time_busy / HOURS_TO_MINUTES
            # Clamp to zero: a station credited for an in-progress unload at
            # end-of-simulation can have time_busy marginally exceed duration_mins.
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
        self.logger.info("Saved report to %s", path)
