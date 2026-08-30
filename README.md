# Echoes of Ember

An original, colorful 2D platform adventure starring Nova, an explorer searching for Ember Shards. The project is being built in tested, playable phases with Python and Pygame.

## Current status

Phase 0 provides the application foundation: a 1280×720 internal canvas, scalable window, fullscreen toggle, frame limiting, logging, and failure-tolerant asset loading.

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

Press `F11` to switch between windowed and fullscreen mode. Press `Esc` or close the window to quit.

For CI or headless verification:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --smoke-test
```

## Project architecture

- `core/`: application lifecycle and shared services
- `assets/`: replaceable art, sound, music, and font files
- `tests/`: automated checks

Additional gameplay packages will be introduced only when their development phase requires them.
