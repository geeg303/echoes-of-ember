"""Single authoritative product version and designation."""
GAME_NAME = "Echoes of Ember"
__version__ = "0.1.0-alpha"
BUILD_DESIGNATION = "World 1 Vertical Slice"

def version_text() -> str:
    return f"{GAME_NAME} {__version__}\n{BUILD_DESIGNATION}"
