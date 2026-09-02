# Verification Pipeline

The local verification runner orchestrates existing authoritative tools and propagates a nonzero exit code on the first failed stage. It performs no network calls and points user data at a temporary directory.

## Quick

```bash
python -m tools.verify_project --quick
```

Runs compilation, standard tests excluding `slow`, all five level validators, World Map validation, narrative validation, achievement validation, and `git diff --check`. This is the normal development loop.

## Full

```bash
python -m tools.verify_project --full
```

Runs the full standard test suite and content checks, then automatically starts and exits normal, isolated slot, direct-level, editor, and debug modes. It finishes with a 3,000-frame boss soak.

## Release

```bash
python -m tools.verify_project --release
```

Includes every full stage, the seven-scenario 600-frame performance benchmark, and the 18,000-frame stability soak. It is release groundwork only; it does not package or upload the game.

## Reports, output, and exit codes

Pass `--json path/to/report.json` to write timestamp, Python/platform information, total duration, commands, per-stage duration, captured output, and pass/fail state. Reports remain local. Console output is deliberately concise:

```text
[PASS] compile
[PASS] tests — 384 passed ...
[PASS] content
FINAL: PASS
```

Exit code 0 means every configured stage passed. Exit code 1 means a stage failed or timed out; the runner prints the relevant tail of output. Invalid runner arguments use argparse's nonzero exit behavior.

Normal pytest owns deterministic behavioral coverage. Full/release modes own process smoke checks and soaks. Hardware-sensitive frame timings remain benchmark evidence, not brittle test thresholds.

