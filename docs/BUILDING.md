# Building Echoes of Ember

## Prerequisites

Use Python 3.11 or newer on the operating system being targeted. Create a virtual environment and install `requirements-build.txt`. The verified Linux environment used Python 3.14.6, pygame-ce 2.5.8, and PyInstaller 6.22.2.

## Commands

```bash
python -m pip install -r requirements-build.txt
python -m tools.build_release --player --clean
python -m tools.build_release --developer --skip-verification
```

The first command performs full release verification by default. `--skip-verification` is an explicit internal repeat-build optimization; do not use it for the first release candidate. `--clean` removes only the repository's known generated `packaging/build`, `packaging/dist`, and `release` directories. User-selected output paths are intentionally unsupported.

Builds are one-directory applications. Player Windows builds use the windowed subsystem; developer builds retain developer/editor modes. Build Windows on Windows, macOS on macOS, and Linux on Linux—PyInstaller is not a cross-compiler. Signing, notarization, installers, one-file mode, and store packaging are outside this phase.

Outputs appear under ignored `release/` paths. Each build contains the executable, PyInstaller runtime, `README.txt`, `THIRD_PARTY_NOTICES.txt`, `BUILD_INFO.json`, and `RESOURCE_MANIFEST.json`, plus a ZIP and `.sha256` file.

## Troubleshooting

Review `packaging/build/<flavor>/<name>/warn-<name>.txt`. Platform-only modules (`winreg`, `_winapi`, `_scproxy`, `msvcrt`) and optional pygame integrations (`numpy`, OpenGL) are expected when absent on Linux. Investigate any missing project module or SDL library. Never suppress the warning report wholesale.
