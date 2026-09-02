"""Authoritative read-only resource and writable user-data locations."""
from __future__ import annotations
import os
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]

def resource_root(*, frozen: bool | None = None, bundle_root: str | Path | None = None) -> Path:
    """Return the source root or PyInstaller's read-only bundle root."""
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if is_frozen:
        candidate = bundle_root if bundle_root is not None else getattr(sys, "_MEIPASS", None)
        if candidate is None:
            raise RuntimeError("packaged resource root is unavailable")
        return Path(candidate).resolve()
    return SOURCE_ROOT

def user_data_root(*, platform: str | None = None, home: Path | None = None) -> Path:
    """Return an OS-appropriate writable root, separate from resources."""
    override = os.environ.get("ECHOES_USER_DATA_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    platform_name = sys.platform if platform is None else platform
    home_root = Path.home() if home is None else home
    if platform_name == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", home_root / "AppData" / "Local"))
    elif platform_name == "darwin":
        base = home_root / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", home_root / ".local" / "share"))
    return base / "echoes_of_ember"

RESOURCE_ROOT = resource_root()
ASSET_ROOT = RESOURCE_ROOT / "assets"
DATA_ROOT = RESOURCE_ROOT / "data"
