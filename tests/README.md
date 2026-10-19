# Tests

80 unit tests built on the standard library's `unittest`. There is nothing to install, and the full suite runs in under a second.

```bash
python3 -m unittest discover -s tests -v                 # everything
python3 -m unittest tests.test_engine -v                 # one file
python3 -m unittest tests.test_engine.TestQueueing -v    # one class
```

The same command runs on GitHub Actions for every push and pull request to `main` ([`tests.yml`](../.github/workflows/tests.yml)).

## Strategy

A simulation is hard to check by eye, because almost any output looks plausible. The tests handle the randomness in two ways:

1. **Remove it.** `StubRandom` replaces the engine's random generator and returns fixed mining and unload durations, so the expected result of a run can be worked out by hand. The engine calls `self.rng.randint(...)`, so a test just sets `engine.rng = StubRandom(...)` after creating the engine. Each argument is either a fixed value or a list consumed in order.
2. **Check rules that hold for any run.** The real generator runs across 30 combinations of seeds and truck/station counts, and each test checks a statement that must always be true, such as "a station is never busy longer than the simulation lasts".

## What each file covers

| File | Tests | Covers |
|---|---|---|
| [`test_engine.py`](test_engine.py) | 39 | Hand-calculated scenarios, queueing rules, end-of-run accounting, invariants, edge cases, reproducibility |
| [`test_reporting.py`](test_reporting.py) | 14 | Metric math against hand-set numbers, exact Markdown rows, saving files |
| [`test_models.py`](test_models.py) | 14 | `SimConfig` defaults, validation, and immutability; `Event` ordering on a heap |
| [`test_cli.py`](test_cli.py) | 13 | Argument parsing, rejecting bad input, stdout vs. stderr, `--output` |

### `test_engine.py` in detail

| Class | Examples |
|---|---|
| `TestSingleTruckScenarios` | One 150-minute cycle (1 h mine, 30 min travel, 30 min unload, 30 min travel) delivers exactly one load. An event exactly at the end time still counts. |
| `TestQueueing` | Two trucks at one station wait 0 and 30 min, and four trucks wait 0, 30, 60, and 90. A free station is used before anyone queues. A truck joins the station with the shorter wait. |
| `TestEndOfRunAccounting` | Mining, travel, waiting, or unloading still in progress when the run ends is credited up to the end time, so every truck's time totals add up to the full duration. |
| `TestRunOnce` | Calling `run()` a second time raises `RuntimeError` and leaves the results untouched. |
| `TestInvariants` | No negative times; loads delivered equals trucks served; truck unload time equals station busy time; random draws stay within the spec's ranges; no waiting when there are at least as many stations as trucks. |
| `TestEdgeCases` | A 1-hour run delivers nothing. One station shared by 50 trucks stays over 90% busy. |
| `TestReproducibility` | The same seed gives identical results, and the engine leaves the global `random` state untouched. |

## Regression tests for fixed bugs

The suite originally caught three bugs. Each was tracked as an `@unittest.expectedFailure` test until it was fixed. Those tests now run as normal regression tests:

| Issue | Tests |
|---|---|
| [#5](https://github.com/sbasu107/lunar-He3-mining-sim/issues/5): time still in progress at the end of a run was not counted | `TestEndOfRunAccounting` |
| [#6](https://github.com/sbasu107/lunar-He3-mining-sim/issues/6): calling `run()` twice corrupted results | `TestRunOnce` |
| [#7](https://github.com/sbasu107/lunar-He3-mining-sim/issues/7): `SimConfig` did not validate its values | `test_rejects_non_positive_values` and `test_error_names_the_invalid_field` in `test_models.py` |
