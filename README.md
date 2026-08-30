# Echoes of Ember

An original, colorful 2D platform adventure starring Nova, an explorer searching for Ember Shards. The project is being built in tested, playable phases with Python and Pygame.

## Current status

Phase 5 is playable. Nova now has reusable animation, health and lives, data-driven collectibles, score tracking, pickup feedback, and a polished fixed-screen HUD while exploring the validated multi-screen parallax level.

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
- Debug full-level restart: `F7` when `DEBUG_MODE` is enabled

For CI or headless verification:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --smoke-test
```

## Project architecture

- `core/`: application lifecycle and shared services
- `entities/`: Nova and future moving game objects
- `entities/collectible.py`: reusable animated pickup entities and original placeholder art
- `world/`: validated levels, tile definitions, tile maps, and collision resolution
- `world/camera.py`: smooth tracking and world-to-screen framing
- `world/background.py`: procedural multi-layer parallax scenery
- `systems/animation.py`: reusable named clips, timing, events, looping, and flipping
- `systems/player_animation.py`: Nova's animation configuration and generated placeholder art
- `systems/progression.py`: centralized score and per-level collectible tracking
- `systems/collectible_system.py`: pickup lifecycle, culling, and lightweight effects
- `ui/debug_overlay.py`: animation and movement diagnostics in debug builds
- `ui/hud.py`: fixed-screen health, lives, shard, score, level, and power-up display
- `data/levels/`: external JSON level content
- `tools/`: content validation utilities
- `assets/`: replaceable art, sound, music, and font files
- `tests/`: automated checks

Additional gameplay packages will be introduced only when their development phase requires them.

## Player animation

Nova currently supports `idle`, `run`, `jump`, `fall`, `land`, `hurt`, `attack`, and `death`. Clips are configured with a frame count, FPS, loop mode, and optional frame events in `systems/player_animation.py`. The controller accepts ordinary Pygame surfaces, so generated frames can later be replaced by sliced PNG sprite-sheet frames without changing player movement or state logic.

All placeholder frames are original Pygame-drawn shapes. They share a stable bottom-center visual anchor while Nova's 44×62 collision rectangle remains independent and unchanged. Left-facing art is generated at render time by horizontal flipping rather than duplicated frame sets.

When `DEBUG_MODE` is enabled, the lower-left overlay reports the current animation, frame index, facing direction, grounded state, and velocity.

## Collectibles and score

The current level deliberately places four collectible types:

- Ember Shard: 100 points; the primary collectible, tracked as a collected/total pair.
- Rare Crystal: 1,000 points; an optional elevated-route reward.
- Secret Token: 2,500 points; a separately tracked exploration reward.
- Health Item: 0 points; restores one health and remains available while Nova is already at full health.

Collectibles animate through the same generic controller used by player animation. Their overlap rectangles remain in world coordinates, their render positions use the camera offset, and far-off collectibles are neither drawn nor animated. Pickup sounds use failure-tolerant asset hooks, so absent audio files produce silence rather than crashes.

Collected objects and score persist through hazard respawns. `F7` performs a full level restart, restoring every object from JSON and clearing current-level score and counters. Save-file persistence is intentionally deferred to the save-system phase.

### Level object format

Collectibles are authored in the level's `objects` array:

```json
{
  "objects": [
    {
      "id": "shard_01",
      "type": "ember_shard",
      "x": 200,
      "y": 970
    }
  ]
}
```

Supported `type` values are `ember_shard`, `rare_crystal`, `secret_token`, and `health_item`. IDs must be unique when provided; coordinates must be finite and inside the level's pixel bounds. Invalid objects stop level loading with a descriptive validation error.

## HUD

The HUD remains fixed to the screen while the world scrolls. It contains three health hearts, remaining lives, Ember Shards collected versus available, current score, level name, and a reserved power-up slot. Shard and score values pulse briefly after pickups, while health changes flash the heart display.

Nova starts with three health and three lives. Hazards remove one health and return Nova to the level spawn while preserving collected objects. Reaching zero health plays the death animation, consumes one life, restores health, and respawns. Because the game-over state is scheduled for a later phase, play currently continues when the displayed lives counter reaches zero.
