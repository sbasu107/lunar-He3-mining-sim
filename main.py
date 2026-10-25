"""Command-line entry point for the lunar He-3 mining simulation.

Usage:
    python3 main.py [n] [m] [--hours H] [--seed S] [--output PATH] [--log-level LEVEL]

Examples:
    python3 main.py                      # 10 trucks, 3 stations, 72 hours
    python3 main.py 20 5                 # 20 trucks, 5 stations
    python3 main.py 10 3 --seed 42 --output results/summary_report.md
    python3 main.py --log-level debug    # trace every event on stderr
"""

import argparse
import logging
import sys
import time

from mining import MiningSimulation, Reporter, SimConfig
from sim_engine import SimulationEngine

DEFAULT_TRUCKS = 10
DEFAULT_STATIONS = 3
DEFAULT_HOURS = 72
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
DEFAULT_LOG_LEVEL = "WARNING"


def positive_int(value: str) -> int:
    """argparse type that accepts only integers >= 1."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer")
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1 (got {number})")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate a lunar Helium-3 mining operation with n trucks "
                    "and m unload stations.",
    )
    parser.add_argument(
        "trucks", metavar="n", type=positive_int, nargs="?",
        default=DEFAULT_TRUCKS,
        help=f"number of mining trucks (default: {DEFAULT_TRUCKS})",
    )
    parser.add_argument(
        "stations", metavar="m", type=positive_int, nargs="?",
        default=DEFAULT_STATIONS,
        help=f"number of unload stations (default: {DEFAULT_STATIONS})",
    )
    parser.add_argument(
        "--hours", type=positive_int, default=DEFAULT_HOURS,
        help=f"simulated duration in hours (default: {DEFAULT_HOURS})",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="random seed for reproducible runs (default: random)",
    )
    parser.add_argument(
        "--output", metavar="PATH", default=None,
        help="also save the Markdown report to PATH "
             "(e.g. results/summary_report.md)",
    )
    parser.add_argument(
        "--log-level", type=str.upper, choices=LOG_LEVELS, default=DEFAULT_LOG_LEVEL,
        help=f"log detail written to stderr (default: {DEFAULT_LOG_LEVEL})",
    )
    return parser


def configure_logging(level: str) -> None:
    """Send log records at ``level`` and above to stderr."""
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)

    config = SimConfig(
        num_trucks=args.trucks,
        num_stations=args.stations,
        duration_hours=args.hours,
        random_seed=args.seed,
    )

    sim_logger = logging.getLogger("simulation.engine")
    sim_logger.info(
        "Starting simulation: %d trucks, %d stations, %d h (seed=%s)",
        config.num_trucks,
        config.num_stations,
        config.duration_hours,
        config.random_seed,
    )

    start = time.perf_counter()
    engine = SimulationEngine()
    scenario = MiningSimulation(engine, config, logger=sim_logger)
    scenario.setup()
    engine.run(until=config.duration_minutes)
    scenario.finalize(until=config.duration_minutes)
    elapsed = time.perf_counter() - start

    sim_logger.info(
        "Simulation finished at t=%.0f min: %d events processed, %d loads delivered",
        engine.clock,
        engine.events_processed,
        sum(t.loads_delivered for t in scenario.trucks),
    )

    reporter = Reporter(
        trucks=scenario.trucks,
        stations=scenario.stations,
        config=config,
        seed=scenario.seed,
    )
    reporter.print_report()

    if args.output:
        reporter.save_markdown(args.output)
        print(f"Report saved to {args.output}", file=sys.stderr)

    print(
        f"Simulated {config.duration_hours} h in {elapsed * 1000:.1f} ms "
        "of real world time.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
