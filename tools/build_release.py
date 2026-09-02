"""Reproducible one-directory PyInstaller release builder."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

from core.version import BUILD_DESIGNATION, GAME_NAME, __version__
from settings import PROJECT_ROOT

GENERATED_ROOTS = (PROJECT_ROOT / "packaging/build", PROJECT_ROOT / "packaging/dist", PROJECT_ROOT / "release")
RESOURCE_DIRS = ("assets", "data")

def safe_clean(target: Path, allowed_root: Path) -> None:
    target, allowed_root = target.resolve(), allowed_root.resolve()
    if target == allowed_root or allowed_root not in target.parents:
        raise ValueError(f"refusing to clean unsafe path: {target}")
    if target.exists():
        shutil.rmtree(target)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def resource_inventory(root: Path = PROJECT_ROOT) -> list[dict[str, object]]:
    entries = []
    for directory in RESOURCE_DIRS:
        source = root / directory
        if not source.is_dir():
            raise FileNotFoundError(f"required resource directory missing: {source}")
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            entries.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": sha256(path)})
    if not entries:
        raise RuntimeError("resource inventory is empty")
    return entries

def platform_slug() -> tuple[str, str, str]:
    system = platform.system().lower()
    system = {"darwin": "macos"}.get(system, system)
    machine = platform.machine().lower() or "unknown"
    suffix = ".exe" if os.name == "nt" else ""
    return system, machine, suffix

def artifact_stem(flavor: str) -> str:
    system, machine, _ = platform_slug()
    return f"EchoesOfEmber-{__version__}-{system}-{machine}-{flavor}"

def verify_manifest(package: Path, manifest: list[dict[str, object]]) -> None:
    resource_base = package / "_internal" if (package / "_internal").is_dir() else package
    for entry in manifest:
        target = resource_base / str(entry["path"])
        if not target.is_file() or target.stat().st_size != entry["size"] or sha256(target) != entry["sha256"]:
            raise RuntimeError(f"packaged resource mismatch: {entry['path']}")

def run_checked(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, **kwargs)

def build(flavor: str, *, verify_source: bool, clean: bool) -> Path:
    if flavor not in {"player", "developer"}:
        raise ValueError("flavor must be player or developer")
    if verify_source:
        run_checked([sys.executable, "-m", "tools.verify_project", "--release"], cwd=PROJECT_ROOT)
    build_root, dist_root, release_root = GENERATED_ROOTS
    if clean:
        for target in GENERATED_ROOTS:
            safe_clean(target, PROJECT_ROOT)
    build_root.mkdir(parents=True, exist_ok=True); dist_root.mkdir(parents=True, exist_ok=True); release_root.mkdir(parents=True, exist_ok=True)
    name = "EchoesOfEmber" if flavor == "player" else "EchoesOfEmberDeveloper"
    entry = PROJECT_ROOT / "packaging" / f"{flavor}_entry.py"
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--name", name,
               "--paths", str(PROJECT_ROOT), "--workpath", str(build_root / flavor), "--distpath", str(dist_root / flavor),
               "--specpath", str(build_root / "specs")]
    if flavor == "player": command.append("--windowed")
    else: command += ["--hidden-import", "tools.level_editor"]
    for directory in RESOURCE_DIRS:
        command += ["--add-data", f"{PROJECT_ROOT / directory}{os.pathsep}{directory}"]
    command.append(str(entry)); run_checked(command, cwd=PROJECT_ROOT)
    pyinstaller_package = dist_root / flavor / name
    output = release_root / artifact_stem(flavor)
    safe_clean(output, release_root); shutil.copytree(pyinstaller_package, output)
    manifest = resource_inventory(); (output / "RESOURCE_MANIFEST.json").write_text(json.dumps({"resources": manifest}, indent=2) + "\n")
    commit = run_checked(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True).stdout.strip()
    metadata = {"application": GAME_NAME, "version": __version__, "designation": BUILD_DESIGNATION, "flavor": flavor,
                "git_commit": commit, "built_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
                "pygame": importlib.metadata.version("pygame-ce"), "pyinstaller": importlib.metadata.version("pyinstaller"),
                "platform": platform.platform(), "architecture": platform.machine()}
    (output / "BUILD_INFO.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    shutil.copy2(PROJECT_ROOT / "THIRD_PARTY_NOTICES.txt", output)
    readme = "README_DISTRIBUTION.txt" if flavor == "player" else "README_DEVELOPER.txt"
    shutil.copy2(PROJECT_ROOT / "packaging" / readme, output / "README.txt")
    verify_manifest(output, manifest)
    executable = output / (name + platform_slug()[2])
    if not executable.is_file(): raise RuntimeError("packaged executable missing")
    with tempfile.TemporaryDirectory(prefix="echoes-package-") as temporary:
        cwd = Path(temporary) / "cwd"; profile = Path(temporary) / "profile"; cwd.mkdir()
        env = os.environ.copy(); env.update({"SDL_VIDEODRIVER":"dummy", "SDL_AUDIODRIVER":"dummy", "ECHOES_USER_DATA_ROOT":str(profile), "PYTHONPATH":""})
        run_checked([str(executable), "--version"], cwd=cwd, env=env, capture_output=True)
        run_checked([str(executable), "--smoke-test"], cwd=cwd, env=env, capture_output=True)
        self_test_env = env.copy(); self_test_env["ECHOES_PACKAGE_SELF_TEST"] = "1"
        run_checked([str(executable), "--package-self-test"], cwd=cwd, env=self_test_env, capture_output=True)
        if flavor == "player":
            denied = subprocess.run([str(executable), "--debug", "--smoke-test"], cwd=cwd, env=env, capture_output=True)
            if denied.returncode != 2: raise RuntimeError("player build accepted developer CLI")
            run_checked([str(executable), "--slot", "1", "--smoke-test"], cwd=cwd, env=env, capture_output=True)
            if not (profile / "saves/slot_1.json").is_file(): raise RuntimeError("packaged save was not created outside resources")
            if not (profile / "settings.json").is_file() or not (profile / "achievements.json").is_file(): raise RuntimeError("packaged preferences were not persisted")
        else:
            for args in (("--level","verdant_03","--smoke-test"),("--debug","--level","verdant_boss","--smoke-test"),("--editor","--level","verdant_04","--smoke-test")):
                run_checked([str(executable), *args], cwd=cwd, env=env, capture_output=True)
    archive_base = release_root / artifact_stem(flavor)
    archive = Path(shutil.make_archive(str(archive_base), "zip", root_dir=release_root, base_dir=output.name))
    checksum = sha256(archive); archive.with_suffix(archive.suffix + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    with zipfile.ZipFile(archive) as handle:
        if handle.testzip() is not None: raise RuntimeError("archive integrity check failed")
    print(output); print(archive); print(checksum)
    return output

def main() -> int:
    parser = argparse.ArgumentParser(description="Build Echoes of Ember distributions")
    group = parser.add_mutually_exclusive_group(required=True); group.add_argument("--player", action="store_true"); group.add_argument("--developer", action="store_true")
    parser.add_argument("--clean", action="store_true"); parser.add_argument("--skip-verification", action="store_true", help="internal repeat build only")
    args = parser.parse_args(); build("player" if args.player else "developer", verify_source=not args.skip_verification, clean=args.clean); return 0

if __name__ == "__main__": raise SystemExit(main())
