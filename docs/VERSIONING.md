# Versioning

`core/version.py` is the single authoritative version source. Echoes of Ember uses SemVer-like `0.MINOR.PATCH` versions while content is incomplete. A prerelease suffix communicates stability or audience when useful.

`0.1.0-alpha` designates the verified World 1 Vertical Slice. Patch releases may contain compatible fixes and packaging refinements. A future content milestone may advance the minor version, but no exact Worlds 2–4 versions are promised here. Version 1.0 is reserved for a separately defined complete-game release milestone.

The builder records version, designation, Git commit, UTC build time, flavor, Python, pygame-ce, PyInstaller, platform, and architecture in `BUILD_INFO.json`. A future verified prerelease tag may be `v0.1.0-alpha`; Phase 26 does not create it automatically.
