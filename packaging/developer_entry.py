"""Frozen internal developer-distribution entry point."""
import os
os.environ["ECHOES_BUILD_FLAVOR"] = "developer"
from main import main
raise SystemExit(main())
