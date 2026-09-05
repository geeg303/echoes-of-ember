# Packaging Report — 0.1.0-alpha

## Environment

- Designation: World 1 Vertical Slice
- Host: Linux 7.2.2, CachyOS, glibc 2.44, x86_64
- Python: 3.14.6
- pygame-ce: 2.5.8
- PyInstaller: 6.22.2
- Source commit embedded in both artifacts: `0a238f77f0a7da65a71e768dd5f71af2f426fc1e`

## Artifacts

| Flavor | Executable | Unpacked | ZIP | SHA-256 |
|---|---|---:|---:|---|
| Player | `EchoesOfEmber` | 60 MB | 27 MB | `b5667dc7bc5e3e866782096e28c93fb5255414f62c82af4897df0b8e89aeaca5` |
| Developer | `EchoesOfEmberDeveloper` | 60 MB | 27 MB | `e34dad1770c994c4a031b7677aca455c840ed5893101003c0c1b007a96fb899c` |

Both archives passed SHA-256 verification and ZIP integrity checking. The player archive was extracted to a temporary directory unrelated to the repository; its executable passed `--version` and dummy-video/audio smoke startup there with an empty `PYTHONPATH`. Observed headless smoke startup was approximately 0.531 seconds.

The manifest contains all 94 files under `assets/` and `data/`, including levels, world map, boss, NPC, dialogue, achievement, audio catalogs, and generated sounds/music. Every packaged file matched source size and SHA-256.

The player build rejected debug mode with exit status 2. The developer build passed normal, direct-level, boss-debug, and editor smoke modes. With an isolated `ECHOES_USER_DATA_ROOT`, the packaged runtime created and reloaded campaign saves, settings, and achievement state outside the application directory.

## Warning review

PyInstaller reported conditional platform modules (`winreg`, `_winapi`, `_scproxy`, `msvcrt`, Java/VMS helpers) and optional pygame integrations (`numpy`, OpenGL, typing extensions discovery). No missing Echoes of Ember module, required SDL library, or runtime resource was reported. Actual packaged smoke, content loading, editor, and persistence checks passed, so these warnings are categorized as expected for this Linux build.

No application icon was added: the repository does not yet contain approved final icon artwork, and Linux execution does not require one. Windows/macOS metadata and icon work remain native-platform release tasks.

## Human and platform limits

The artifact was launched automatically, not manually judged through a physical display/audio/controller setup. Windows and macOS were not built. Secondary-machine compatibility, fullscreen quality, subjective audio, physical controllers, antivirus reputation, signing, and notarization remain human/native-platform checks.
