"""Tests for the command-line entry point (main.py)."""

import argparse
import io
import logging
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import main as cli


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Run main() and capture (exit code, stdout, stderr).

    main() reconfigures the root logger, so its handlers and level are
    restored afterwards to keep tests independent.
    """
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
    return code, out.getvalue(), err.getvalue()


class TestParser(unittest.TestCase):
    def parse(self, argv):
        return cli.build_parser().parse_args(argv)

    def test_defaults(self):
        args = self.parse([])
        self.assertEqual((args.trucks, args.stations, args.hours), (10, 3, 72))
        self.assertIsNone(args.seed)
        self.assertIsNone(args.output)
        self.assertEqual(args.log_level, "WARNING")

    def test_log_level_is_case_insensitive(self):
        for value in ("debug", "Info", "WARNING", "error"):
            with self.subTest(value=value):
                self.assertEqual(self.parse(["--log-level", value]).log_level, value.upper())

    def test_positional_n_and_m(self):
        args = self.parse(["20", "5"])
        self.assertEqual((args.trucks, args.stations), (20, 5))

    def test_only_n_keeps_default_m(self):
        args = self.parse(["7"])
        self.assertEqual((args.trucks, args.stations), (7, 3))

    def test_optional_flags(self):
        args = self.parse(["4", "2", "--hours", "24", "--seed", "9", "--output", "x.md"])
        self.assertEqual(args.hours, 24)
        self.assertEqual(args.seed, 9)
        self.assertEqual(args.output, "x.md")

    def test_flags_before_positionals(self):
        args = self.parse(["--seed", "1", "4", "2"])
        self.assertEqual((args.trucks, args.stations, args.seed), (4, 2, 1))

    def test_invalid_input_exits_with_usage_error(self):
        for argv in (["0"], ["-1"], ["abc"], ["1.5"], ["3", "0"],
                     ["1", "2", "3"], ["--hours", "0"], ["--seed", "x"],
                     ["--log-level", "loud"]):
            with self.subTest(argv=argv):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                    self.parse(argv)
                self.assertEqual(ctx.exception.code, 2)


class TestPositiveInt(unittest.TestCase):
    def test_accepts_positive_integers(self):
        self.assertEqual(cli.positive_int("1"), 1)
        self.assertEqual(cli.positive_int("250"), 250)

    def test_rejects_zero_negative_and_non_integers(self):
        for value in ("0", "-3", "two", "2.0", ""):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    cli.positive_int(value)


class TestMain(unittest.TestCase):
    def test_prints_report_for_requested_configuration(self):
        code, out, _ = run_cli(["4", "2", "--hours", "5", "--seed", "1"])
        self.assertEqual(code, 0)
        self.assertIn("**Mining Trucks (n):** 4", out)
        self.assertIn("**Unload Stations (m):** 2", out)
        self.assertIn("**Simulation Duration:** 5 hours", out)
        self.assertIn("**Random Seed:** 1", out)

    def test_status_messages_go_to_stderr_not_stdout(self):
        _, out, err = run_cli(["--seed", "1"])
        self.assertIn("Simulated 72 h", err)
        self.assertNotIn("Simulated 72 h", out)
        self.assertTrue(out.startswith("# Lunar Helium-3 Mining Simulation"))

    def test_same_seed_gives_identical_output(self):
        _, first, _ = run_cli(["10", "3", "--seed", "42"])
        _, second, _ = run_cli(["10", "3", "--seed", "42"])
        self.assertEqual(first, second)

    def test_does_not_write_file_without_output_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                run_cli(["--seed", "1"])
                self.assertEqual(os.listdir(tmp), [])
            finally:
                os.chdir(cwd)

    def test_output_flag_saves_same_report_as_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results", "report.md")
            _, out, err = run_cli(["--seed", "1", "--output", path])
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), out.strip())
            self.assertIn(path, err)


class TestLogLevel(unittest.TestCase):
    def test_default_level_writes_no_log_records(self):
        _, _, err = run_cli(["--seed", "1"])
        self.assertNotIn("INFO", err)
        self.assertNotIn("DEBUG", err)

    def test_info_level_logs_run_summary_to_stderr(self):
        _, out, err = run_cli(["--seed", "1", "--log-level", "info"])
        self.assertIn("INFO simulation.engine: Starting simulation: 10 trucks", err)
        self.assertIn("INFO simulation.engine: Simulation finished at t=4320 min", err)
        self.assertNotIn("DEBUG", err)
        self.assertNotIn("simulation.engine", out)

    def test_debug_level_traces_events(self):
        _, _, err = run_cli(["1", "1", "--hours", "2", "--seed", "1", "--log-level", "debug"])
        self.assertIn("DEBUG simulation.engine: t=", err)

    def test_logging_does_not_change_the_report(self):
        _, quiet, _ = run_cli(["--seed", "42"])
        _, verbose, _ = run_cli(["--seed", "42", "--log-level", "debug"])
        self.assertEqual(quiet, verbose)


if __name__ == "__main__":
    unittest.main()
