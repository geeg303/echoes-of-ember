"""Frozen player-distribution entry point."""
import os
os.environ["ECHOES_BUILD_FLAVOR"] = "player"
from main import main
raise SystemExit(main())
