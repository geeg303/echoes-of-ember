"""One-command local verification pipeline for Echoes of Ember."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from settings import PROJECT_ROOT


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    command: tuple[str, ...]
    timeout: int = 120


@dataclass(slots=True)
class StageResult:
    name: str
    passed: bool
    duration_seconds: float
    command: list[str]
    output: str
    returncode: int


def build_stages(mode: str) -> tuple[Stage, ...]:
    py = sys.executable
    tests = (py, "-m", "pytest", "-q")
    if mode == "quick":
        tests += ("-m", "not slow")
    stages = [
        Stage("compile", (py, "-m", "compileall", "-q", ".")),
        Stage("tests", tests, 240),
        Stage("content", (py, "-m", "tools.validation", "--all-levels")),
        Stage("git-diff-check", ("git", "diff", "--check")),
    ]
    if mode in {"full", "release"}:
        stages.extend([
            Stage("smoke-normal", (py, "main.py", "--smoke-test")),
            Stage("smoke-slot", (py, "main.py", "--slot", "1", "--smoke-test")),
            Stage("smoke-level", (py, "main.py", "--level", "verdant_03", "--smoke-test")),
            Stage("smoke-editor", (py, "main.py", "--editor", "--level", "verdant_04", "--smoke-test")),
            Stage("smoke-debug", (py, "main.py", "--debug", "--level", "verdant_boss", "--smoke-test")),
            Stage("short-soak", (py, "-m", "tools.soak_test", "--frames", "3000", "--draw-every", "30"), 180),
        ])
    if mode == "release":
        stages.extend([
            Stage("performance", (py, "-m", "tools.performance_benchmark", "--all", "--frames", "600"), 240),
            Stage("long-soak", (py, "-m", "tools.soak_test", "--frames", "18000", "--draw-every", "30"), 300),
        ])
    return tuple(stages)


def run_stage(stage: Stage, environment: dict[str, str]) -> StageResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            stage.command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=stage.timeout,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = f"timed out after {stage.timeout}s\n{exc.stdout or ''}\n{exc.stderr or ''}".strip()
        returncode = 124
    return StageResult(
        stage.name, returncode == 0, round(time.perf_counter() - started, 3),
        list(stage.command), output, returncode,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Echoes of Ember locally")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--quick", action="store_const", dest="mode", const="quick")
    modes.add_argument("--full", action="store_const", dest="mode", const="full")
    modes.add_argument("--release", action="store_const", dest="mode", const="release")
    parser.set_defaults(mode="quick")
    parser.add_argument("--json", type=Path, dest="json_path", help="write a machine-readable local report")
    args = parser.parse_args()

    environment = os.environ.copy()
    environment.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYTHONHASHSEED="0")
    results: list[StageResult] = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="echoes-verify-") as user_root:
        environment["XDG_DATA_HOME"] = user_root
        for stage in build_stages(args.mode):
            result = run_stage(stage, environment)
            results.append(result)
            detail = ""
            if stage.name == "tests" and result.output:
                detail = " — " + result.output.splitlines()[-1]
            print(f"[{'PASS' if result.passed else 'FAIL'}] {stage.name}{detail}")
            if not result.passed:
                print(result.output[-4000:])
                break

    passed = bool(results) and all(item.passed for item in results) and len(results) == len(build_stages(args.mode))
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": args.mode,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "passed": passed,
        "stages": [asdict(item) for item in results],
    }
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FINAL: {'PASS' if passed else 'FAIL'} ({report['duration_seconds']:.3f}s)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

