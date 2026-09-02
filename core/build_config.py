"""Build-flavor policy shared by source and frozen entry points."""
from __future__ import annotations
import os
from enum import Enum

class BuildFlavor(str, Enum):
    PLAYER = "player"
    DEVELOPER = "developer"

def current_build_flavor() -> BuildFlavor:
    value = os.environ.get("ECHOES_BUILD_FLAVOR", BuildFlavor.DEVELOPER.value)
    try:
        return BuildFlavor(value)
    except ValueError as exc:
        raise RuntimeError(f"invalid build flavor: {value}") from exc

def developer_features_available() -> bool:
    return current_build_flavor() is BuildFlavor.DEVELOPER
