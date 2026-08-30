# Echoes of Ember

An original, colorful 2D platform adventure starring Nova, an explorer searching for Ember Shards. The project is being built in tested, playable phases with Python and Pygame.

## Current status

Phase 4 is playable. Nova now uses a reusable frame-animation controller and original procedural animation frames while exploring the validated multi-screen tile level and parallax world.

## Requirements

- Python 3.11 or newer
- Pygame Community Edition 2.5.6 or newer (the maintained Pygame-compatible package)

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Linux or macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the game

```bash
python main.py
```

### Controls

- Move: `A`/`D` or left/right arrows
- Jump: `Space`, `Z`, or up arrow (release early for a shorter jump)
- Toggle fullscreen: `F11`
- Quit: `Esc`
- Debug attack animation: `F5` when `DEBUG_MODE` is enabled
- Debug hurt animation: `F6` when `DEBUG_MODE` is enabled

For CI or headless verification:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --smoke-test
```

## Project architecture

- `core/`: application lifecycle and shared services
- `entities/`: Nova and future moving game objects
- `world/`: validated levels, tile definitions, tile maps, and collision resolution
- `world/camera.py`: smooth tracking and world-to-screen framing
- `world/background.py`: procedural multi-layer parallax scenery
- `systems/animation.py`: reusable named clips, timing, events, looping, and flipping
- `systems/player_animation.py`: Nova's animation configuration and generated placeholder art
- `ui/debug_overlay.py`: animation and movement diagnostics in debug builds
- `data/levels/`: external JSON level content
- `tools/`: content validation utilities
- `assets/`: replaceable art, sound, music, and font files
- `tests/`: automated checks

Additional gameplay packages will be introduced only when their development phase requires them.

## Player animation

Nova currently supports `idle`, `run`, `jump`, `fall`, `land`, `hurt`, `attack`, and `death`. Clips are configured with a frame count, FPS, loop mode, and optional frame events in `systems/player_animation.py`. The controller accepts ordinary Pygame surfaces, so generated frames can later be replaced by sliced PNG sprite-sheet frames without changing player movement or state logic.

All placeholder frames are original Pygame-drawn shapes. They share a stable bottom-center visual anchor while Nova's 44×62 collision rectangle remains independent and unchanged. Left-facing art is generated at render time by horizontal flipping rather than duplicated frame sets.

When `DEBUG_MODE` is enabled, the lower-left overlay reports the current animation, frame index, facing direction, grounded state, and velocity.
