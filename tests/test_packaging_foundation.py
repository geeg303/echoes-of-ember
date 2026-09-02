from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys
import pytest

from core.build_config import BuildFlavor, current_build_flavor, developer_features_available
from core.paths import resource_root, user_data_root
from core.version import BUILD_DESIGNATION, __version__, version_text
from tools.build_release import artifact_stem, resource_inventory, safe_clean


def test_version_is_prerelease_vertical_slice() -> None:
    assert __version__ == "0.1.0-alpha"
    assert "World 1 Vertical Slice" in BUILD_DESIGNATION
    assert __version__ in version_text()


def test_source_and_simulated_frozen_resource_roots(tmp_path: Path) -> None:
    assert (resource_root(frozen=False) / "data").is_dir()
    assert resource_root(frozen=True, bundle_root=tmp_path) == tmp_path.resolve()
    with pytest.raises(RuntimeError, match="unavailable"):
        resource_root(frozen=True)


def test_user_data_platform_locations_are_not_resource_bundle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ECHOES_USER_DATA_ROOT", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert user_data_root(platform="linux", home=tmp_path) == tmp_path / ".local/share/echoes_of_ember"
    assert user_data_root(platform="darwin", home=tmp_path) == tmp_path / "Library/Application Support/echoes_of_ember"
    assert user_data_root(platform="win32", home=tmp_path) == tmp_path / "AppData/Local/echoes_of_ember"


def test_user_data_override(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "profile"
    monkeypatch.setenv("ECHOES_USER_DATA_ROOT", str(target))
    assert user_data_root() == target.resolve()


def test_build_flavor_defaults_to_developer_and_player_restricts(monkeypatch) -> None:
    monkeypatch.delenv("ECHOES_BUILD_FLAVOR", raising=False)
    assert current_build_flavor() is BuildFlavor.DEVELOPER
    assert developer_features_available()
    monkeypatch.setenv("ECHOES_BUILD_FLAVOR", "player")
    assert current_build_flavor() is BuildFlavor.PLAYER
    assert not developer_features_available()


def test_version_cli_and_player_cli_restriction() -> None:
    version = subprocess.run([sys.executable, "main.py", "--version"], capture_output=True, text=True, check=True)
    assert __version__ in version.stdout and BUILD_DESIGNATION in version.stdout
    env = os.environ.copy(); env["ECHOES_BUILD_FLAVOR"] = "player"
    denied = subprocess.run([sys.executable, "main.py", "--debug", "--smoke-test"], capture_output=True, text=True, env=env)
    assert denied.returncode == 2
    assert "does not include developer" in denied.stderr


def test_manifest_covers_all_runtime_catalogs() -> None:
    paths = {entry["path"] for entry in resource_inventory()}
    assert "data/worlds/verdant_reaches.json" in paths
    assert "data/bosses/ashen_warden.json" in paths
    assert "data/achievements/achievements.json" in paths
    assert any(str(path).startswith("data/dialogue/") for path in paths)
    assert any(str(path).startswith("data/npcs/") for path in paths)
    assert any(str(path).startswith("assets/music/") for path in paths)


def test_safe_clean_rejects_root_and_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe"):
        safe_clean(tmp_path, tmp_path)
    with pytest.raises(ValueError, match="unsafe"):
        safe_clean(tmp_path.parent, tmp_path)
    generated = tmp_path / "generated"; generated.mkdir(); (generated / "item").write_text("x")
    safe_clean(generated, tmp_path)
    assert not generated.exists()


def test_artifact_name_is_safe_and_versioned() -> None:
    name = artifact_stem("player")
    assert __version__ in name and name.endswith("-player")
    assert "/" not in name and ".." not in name
