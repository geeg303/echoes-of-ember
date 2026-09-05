# Testing Echoes of Ember

## Philosophy and layers

Tests assert authoritative behavior and public outcomes rather than pixel-perfect rendering or incidental collection ordering. The suite combines focused units, subsystem integrations, user-visible scenarios, reload-driven campaign journeys, authored-data validation, and bounded stability checks. Timing-sensitive behavior advances explicit `dt`; tests never sleep to wait for gameplay timers.

The Phase 24 baseline was 312 tests in 14.74 seconds. After Phase 26, the expanded standard suite contains 405 tests, including resource, build-flavor, manifest, safe-clean, version, and packaged-persistence foundations. Durations vary by hardware.

## Isolation and deterministic state

`tests/conftest.py` establishes dummy SDL before game imports and provides isolated temporary save, settings, and achievement managers. `game_factory` disables persistence and achievements unless a scenario explicitly supplies isolated managers, and shuts down every constructed game. `seeded_rng` returns a local seeded generator without modifying global randomness. Subprocess smoke tests set a temporary user-data root through the verification runner.

No automated test should write to the real user-data directory or production level files. Use pytest's `tmp_path`, the isolated manager fixtures, and editor playtest isolation. Avoid wall-clock sleeps, physical controller assumptions, network access, and real audio-device requirements.

## Semantic helpers

`tests/helpers.py` provides:

- `advance_frames(game, count, dt, draw=False)` for controlled simulation;
- `activate_goal(game)` through real proximity and interaction behavior;
- `campaign_result(...)` for valid frozen persistence scenarios.

Helpers should arrange state but must not bypass the behavior under test. Existing fake controller and audio backends remain the authoritative way to test those optional devices.

## Markers and commands

- `pytest -q` runs the standard suite, including short process-level smoke contracts.
- `pytest -q -m "not slow"` omits explicitly slow process checks.
- `pytest -q tests/test_campaign_e2e.py` runs campaign journeys.
- `pytest -q tests/test_content_integrity.py` validates cross-catalog references.
- `python -m tools.verify_project --quick` is the everyday pipeline.
- `python -m tools.verify_project --full` adds launch-mode smoke tests and a short soak.
- `python -m tools.verify_project --release` adds full benchmarks and the 18,000-frame soak.

Markers are `integration`, `scenario`, and `slow`. Performance benchmark thresholds do not belong in ordinary unit assertions because host scheduling varies; deterministic cache, lifecycle, and no-disk-read invariants do.

## Adding tests

1. Put a focused behavior test beside the relevant subsystem tests.
2. Use a scenario file only when several production systems form the behavior.
3. Use public outcomes where possible and tolerances for floating-point movement.
4. For every discovered regression, first capture reproduction, then fix production, then keep the assertion.
5. Validate failure paths with temporary files and monkeypatching—never damage real data.
6. Run quick verification during iteration and full verification before committing.

Persistence tests should save, reconstruct through the real loader, and compare semantic progression. Controller tests feed `FakeControllerBackend` through `InputManager`; keyboard tests feed Pygame events. Editor tests operate on `LevelDocument`, save only under a temporary root, validate the output, and confirm playtest isolation. Debug and direct-level tests must prove campaign and achievement data are unchanged.
