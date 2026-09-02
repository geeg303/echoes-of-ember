"""Process-level launch argument and exit-code contracts."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest


def run_cli(project_root, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    return subprocess.run(
        [sys.executable, "main.py", *arguments],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ("--slot", "4", "--smoke-test"),
        ("--level", "missing", "--smoke-test"),
        ("--editor", "--level", "bad/path", "--smoke-test"),
        ("--debug", "--new-game", "--smoke-test"),
        ("--editor", "--slot", "1", "--smoke-test"),
        ("--level", "verdant_01", "--slot", "1", "--smoke-test"),
    ],
)
def test_invalid_launch_combinations_fail_cleanly(project_root, arguments) -> None:
    outcome = run_cli(project_root, *arguments)
    assert outcome.returncode == 2
    assert "Traceback" not in outcome.stderr


@pytest.mark.slow
@pytest.mark.parametrize(
    "arguments",
    [
        ("--smoke-test",),
        ("--level", "verdant_03", "--smoke-test"),
        ("--editor", "--level", "verdant_04", "--smoke-test"),
        ("--debug", "--level", "verdant_boss", "--smoke-test"),
    ],
)
def test_supported_launch_modes_exit_successfully(project_root, arguments) -> None:
    outcome = run_cli(project_root, *arguments)
    assert outcome.returncode == 0, outcome.stderr

