from __future__ import annotations

import subprocess

from tools.verify_project import Stage, build_stages, run_stage


def test_verification_modes_have_expected_cost_boundaries() -> None:
    quick = {item.name for item in build_stages("quick")}
    full = {item.name for item in build_stages("full")}
    release = {item.name for item in build_stages("release")}
    assert quick < full < release
    assert "short-soak" not in quick and "short-soak" in full
    assert {"performance", "long-soak"} <= release


def test_stage_runner_propagates_nonzero_exit(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 7, "out", "error"))
    result = run_stage(Stage("failure", ("false",)), {})
    assert not result.passed and result.returncode == 7
    assert "out" in result.output and "error" in result.output

