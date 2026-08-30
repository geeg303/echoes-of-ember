# Echoes of Ember

An original, colorful 2D platform adventure starring Nova, an explorer searching for Ember Shards. The project is being built in tested, playable phases with Python and Pygame.

## Current status

Phase 3 is playable. Nova explores an external, validated JSON tile level spanning several screens. A smooth bounded camera provides a dead-zone, horizontal look-ahead, vertical tracking, and shake support over procedural twilight parallax scenery.

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
- `data/levels/`: external JSON level content
- `tools/`: content validation utilities
- `assets/`: replaceable art, sound, music, and font files
- `tests/`: automated checks

Additional gameplay packages will be introduced only when their development phase requires them.
