# Echoes of Ember

An original, colorful 2D platform adventure starring Nova, an explorer searching for Ember Shards. The project is being built in tested, playable phases with Python and Pygame.

## Current status

Phase 16 is playable. Verdant Reaches now combines the complete campaign, secrets, world map, persistent saves, Ashen Warden boss encounter, centralized effects, and a robust optional audio/music/ambience presentation layer.

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

Normal startup opens the title and three-slot campaign front-end. `python main.py --level verdant_01` remains a direct, nonpersistent development launch; `python main.py --slot 1` bypasses the title and resumes that slot on the World Map.

### Controls

- Menus: arrows/WASD, Enter/Space to confirm, Escape to go back
- Pause: `Esc` during gameplay
- Move: `A`/`D` or left/right arrows
- Jump: `Space`, `Z`, or up arrow (release early for a shorter jump)
- Ember Pulse: `F` while the Ember Pulse power-up is active
- Interact with switches: `E`
- Toggle fullscreen: `F11`
- Debug attack animation: `F5` when `DEBUG_MODE` is enabled
- Toggle optional visual effects: `F6` when `DEBUG_MODE` is enabled
- Debug full-level restart: `F7` when `DEBUG_MODE` is enabled
- Toggle master audio mute: `F8` when `DEBUG_MODE` is enabled

For CI or headless verification:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python main.py --smoke-test
```

## Project architecture

- `core/`: application lifecycle and shared services
- `core/audio_manager.py`: optional mixer, buses, SFX policy, music, ambience, and runtime audio settings
- `entities/`: Nova and future moving game objects
- `entities/collectible.py`: reusable animated pickup entities and original placeholder art
- `entities/enemy.py`: common enemy contract and terrain movement helpers
- `entities/projectile.py`: faction-aware reusable projectile foundation
- `enemies/`: separate crawler, flyer, jumper, turret, and armored AI classes
- `world/`: validated levels, tile definitions, tile maps, and collision resolution
- `world/camera.py`: smooth tracking and world-to-screen framing
- `world/background.py`: procedural multi-layer parallax scenery
- `systems/animation.py`: reusable named clips, timing, events, looping, and flipping
- `systems/player_animation.py`: Nova's animation configuration and generated placeholder art
- `systems/progression.py`: centralized score and per-level collectible tracking
- `systems/collectible_system.py`: pickup lifecycle, culling, and lightweight effects
- `systems/enemy_system.py`: activation, stomps, damage, scoring, and cleanup
- `systems/player_combat.py`: Ember Pulse ownership, cooldown, and projectile spawning
- `systems/projectile_system.py`: shared projectile lifetime, terrain collision, culling, and effect events
- `effects/`: typed procedural particle definitions and primitives
- `systems/effects_system.py`: bounded particles, owned emitters, screen effects, and shake requests
- `systems/powerup_system.py`: active slot, timed modifiers, shield interception, and world pickups
- `systems/world_object_system.py`: platform riding, dynamic collision, triggers, and checkpoint state
- `systems/level_completion.py`: lifecycle phases, requirements, results, ratings, and timer formatting
- `entities/level_goal.py`: reusable world-space Ember Gate
- `states/level_complete.py`: fixed-screen results presentation
- `ui/debug_overlay.py`: animation, movement, particle, emitter, and screen-effect diagnostics
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

Collectibles animate through the same generic controller used by player animation. Their overlap rectangles remain in world coordinates, their render positions use the camera offset, and far-off collectibles are neither drawn nor animated. Pickup sounds use stable catalog IDs and the centralized failure-tolerant audio manager, so unavailable devices or missing files never interrupt gameplay.

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

## Enemies and damage

- Ground Crawler patrols terrain, reverses at walls, and avoids configured cliffs.
- Flyer follows a predictable bounded hover and only pursues Nova within its local detection radius.
- Jumper waits between leaps, then biases a jump toward nearby Nova.
- Turret remains fixed and fires faction-tagged projectiles only inside its activation range.
- Armored Enemy patrols like a crawler but survives ordinary stomps and has four health.

Normal enemies can be stomped by descending from above; Nova bounces upward and receives the enemy score only when it actually dies. An armored stomp bounces Nova but deals no damage. Side contact and hostile projectiles remove one health, apply knockback, trigger the hurt animation, and grant 1.25 seconds of flashing invulnerability. Hazards retain their distinct damage-and-spawn-return behavior.

Enemy rewards are Crawler 200, Flyer 300, Jumper 350, Turret 500, and Armored Enemy 750. Score claims are one-shot even while a death animation is still visible.

### Enemy level object format

```json
{
  "id": "crawler_01",
  "type": "enemy",
  "enemy_type": "crawler",
  "x": 1035,
  "y": 988,
  "properties": {
    "speed": 78,
    "cliff_avoidance": true
  }
}
```

Supported enemy types are `crawler`, `flyer`, `jumper`, `turret`, and `armored`. Properties may override validated per-archetype settings such as speed, detection radius, cooldown, projectile speed, jump force, horizontal speed, health, damage, and score reward. Enemy and collectible IDs share one uniqueness namespace.

## Ember Pulse combat

Press `F` while Ember Pulse is active to start Nova's existing attack animation and immediately launch a pulse in the facing direction. Debug mode no longer grants the ability automatically.

Each pulse deals 1 damage, travels at 720 pixels per second, lasts 0.85 seconds, and uses a 0.35-second firing cooldown. At most four player pulses may exist at once. Pulses disappear on solid terrain, enemy impact, or lifetime expiry. Crawler and Flyer have 1 health, Jumper and Turret have 2, and the Armored Enemy has 4; unlike an ordinary stomp, Ember Pulse can defeat armor.

The shared projectile foundation labels ownership with `PLAYER`, `ENEMY`, or `NEUTRAL` factions. Player pulses cannot harm Nova, and hostile turret shots cannot harm enemy allies. Projectiles use local tile queries rather than scanning the whole map, and all are cleared by a full `F7` level restart.

Enemy death rewards remain one-shot when attacks overlap a dying target. Pulse impacts briefly flash and spark; enemy death produces stronger feedback. These lightweight effects are deliberately local until the full particle-system phase.

## Power-ups

Nova has one primary power-up slot. Picking up a different type replaces the current effect; picking up the same timed type refreshes it to full duration. Losing a life or pressing `F7` clears the slot, while ordinary enemy or hazard damage does not. World pickups are restored only by a full level restart.

- Ember Pulse lasts 20 seconds and grants the existing ranged attack.
- Wind Boots last 18 seconds and provide +20% run speed, +15% acceleration, and +5% jump strength without mutating base physics.
- Aether Wing lasts 18 seconds and grants one extra airborne jump, reset by landing. Bounce pads and stomps do not consume or reset it.
- Stone Guard holds one charge until hit, absorbs enemy, projectile, or hazard damage, and grants 0.55 seconds of follow-up protection.

The HUD shows the active name, remaining timed duration or shield charge, pickup/expiration feedback, and a low-time warning. Power-up pickups and effects use procedural original shapes and remain in world space.

```json
{
  "id": "ember_pulse_01",
  "type": "powerup",
  "powerup_type": "ember_pulse",
  "x": 2720,
  "y": 900,
  "properties": {"duration": 20}
}
```

The optional `duration` override must be finite and positive. Supported types are `ember_pulse`, `wind_boots`, `aether_wing`, and `stone_guard`; IDs share the collectible/enemy uniqueness namespace.

## Current limitations

- Audio uses generated temporary WAV placeholders; final composition, mastering, and subjective mix tuning remain future work.
- Collection and enemy state are held in memory only.
- Lives stop at zero without a Game Over transition; the existing death/respawn loop remains safe.
- Campaign progression and permanent result persistence belong to later phases.

## Interactive world objects

All interactive mechanics are authored in the shared level `objects` array, use world coordinates, and render with camera offsets only. Their IDs share the same uniqueness namespace as enemies, collectibles, and power-ups.

Horizontal and vertical moving platforms travel smoothly between an origin and configured endpoint. Nova inherits the platform's per-frame displacement while riding, detaches naturally when jumping, and is left safely behind instead of being pushed through static terrain. Falling platforms warn for 0.65 seconds, accelerate at 1,500 px/s², and reset after 3 seconds. Disappearing platforms cycle through 2.2 seconds solid, 0.65 seconds flashing, and 1.6 seconds hidden/non-solid.

```json
{
  "id": "platform_horizontal_01",
  "type": "moving_platform",
  "x": 3480,
  "y": 820,
  "properties": {
    "movement": "horizontal",
    "distance": 260,
    "speed": 95,
    "width": 128,
    "height": 22
  }
}
```

Ember Pulse destroys cracked breakable tiles; hostile projectiles and ordinary collisions do not. Destroyed blocks remain absent through ordinary damage and life respawns, while `F7` reloads them from JSON.

Switches are activated with `E` and may reference one or several compatible door IDs. Closed and opening doors are solid; fully open doors are non-solid. Validation rejects missing or incompatible references.

```json
{"id": "switch_01", "type": "switch", "x": 4210, "y": 966,
 "properties": {"target_id": "door_01"}}
{"id": "door_01", "type": "door", "x": 4380, "y": 896,
 "properties": {"width": 48, "height": 128, "opening_duration": 0.55}}
```

Checkpoints activate on contact and replace the current respawn position. Nonfatal hazards and life loss return Nova to the latest checkpoint while preserving collectibles, score, defeated enemies, broken blocks, switches, and doors. `F7` restores the initial spawn and all authored state.

## Level metadata and goals

Level identity is explicit and never derived from filenames. Required metadata includes `id`, `world_id`, `level_number`, `display_name`, description, theme, time target, declared collectible totals, completion requirements, rating thresholds, dimensions, spawn, and a top-level goal. Declared totals are checked against authored objects.

Verdant Beginning is `verdant_01` in `verdant_reaches`. Its only required objective is reaching the Ember Gate; collection remains optional. The procedural world-space gate highlights in interaction range and activates with `E`.

```json
"completion_requirements": {"reach_goal": true, "minimum_ember_shards": 0},
"goal": {
  "type": "ember_gate",
  "x": 6690,
  "y": 896,
  "properties": {"requires_interact": true}
}
```

Completion freezes elapsed time, score, collections, unique enemy defeats, deaths, checkpoints, health, and lives in an immutable `LevelResult`. After a 1.5-second safe sequence, the Level Complete screen shows the result and a metadata-driven Bronze, Silver, or Gold rating. Enter/Space displays “Campaign progression coming later”; `R` uses the same full reconstruction as F7.

## Verdant Beginning design

The level follows teach → test → twist across eight sections: a safe arrival trail, a first-enemy lesson, one-way and bounce-pad platforming, Ember Pulse combat and breakables, moving-world traversal, an optional Wind Boots/Aether Wing route choice, a combined checkpointed challenge, and a calm Ember Gate clearing.

Its 52 Ember Shards form lines, arcs, rising trails, route clusters, and a final breadcrumb path. Three Rare Crystals reward raised routes, while one Secret Token occupies a demanding optional path. Timed powers improve shortcuts but are never mandatory.

See [docs/LEVEL_AUTHORING.md](docs/LEVEL_AUTHORING.md) for the reusable authoring workflow, schemas, validation command, and design conventions.


## Verdant Reaches campaign

The registry at `data/worlds/verdant_reaches.json` explicitly orders `verdant_01`, `verdant_02`, `verdant_03`, and `verdant_04`. Continue advances through Verdant Beginning, Whispering Canopy, Emberfall Ravine, and Ruins of the First Flame before showing aggregate runtime statistics. Replays replace the latest result for that level rather than double-counting it; nothing is saved to disk.

```bash
python main.py --level verdant_03
python -m tools.validation --all-levels
```

Unknown level IDs fail cleanly. See `docs/world_1_design.md` for themes, pacing, encounter patterns, checkpoint philosophy, and mechanic progression.


## Secrets and exploration

World 1 contains twelve optional, data-driven discoveries: caches, rooms, challenge rooms, alternate routes, and one secret exit in Ruins of the First Flame. Discoveries award score once, produce queued screen-space notifications, and appear in frozen level/world results. The secret exit records alternate completion while preserving normal campaign order. See `docs/SECRETS_AND_EXPLORATION.md` for schemas, triggers, reset rules, and clue conventions.


## World Map

Normal startup now opens the procedural Verdant Reaches World Map. Travel uses authored node connections and waypoints; completing a level returns Nova to that node and unlocks routes without auto-launching the next stage. Latest run results remain separate from monotonic session discoveries. The Ruins secret exit permanently reveals the in-memory Ember Veil branch, while First Flame Sanctum opens the aggregate World Complete summary. See `docs/WORLD_MAP.md`.

## Persistent campaign saves

Campaign startup now uses one of three versioned JSON slots (`python main.py --slot 1`). Use `--new-game` only when intentionally resetting the selected slot. Saves contain completed level results, monotonic unlocks and discoveries, the last reached map node, timestamps, and cumulative play time. Atomic writes, a last-known-good backup, validation, and controlled corruption recovery protect progress. Direct `--level` development launches are nonpersistent. See [docs/SAVE_SYSTEM.md](docs/SAVE_SYSTEM.md) for the schema, platform-specific location policy, and recovery rules.

## World 1 boss

First Flame Sanctum is now a playable boss destination. Completing Ruins unlocks the Sanctum but no longer completes Verdant Reaches; defeating the original three-phase Ashen Warden is the true world-completion condition. The fight uses shared projectiles, player damage, Stone Guard, an encounter-safe Ember Pulse grant, arena doors, camera bounds, a segmented boss HUD, and persistent boss progression. See [docs/BOSS_SYSTEM.md](docs/BOSS_SYSTEM.md) and [docs/ASHEN_WARDEN.md](docs/ASHEN_WARDEN.md).


## Particle and visual effects

Phase 15 routes transient presentation through one `EffectsSystem`. Definitions are typed, authored once in `effects/definitions.py`, and rendered from Pygame primitives without external artwork. World particles use camera offsets only while screen particles and flashes remain fixed to the 1280×720 canvas. Gameplay remains authoritative: particles never modify collision, damage, timing, AI, progression, results, or save data.

The system covers Nova's jump/land/damage/death feedback; all four power-ups; Ember Pulse launch, trail, and impact; enemy hits, stomps, armor blocks, and defeats; collectible pickups; checkpoints, secrets, breakables, switches, doors, and platform warnings; per-level ambience; Ashen Warden awakening, attacks, vulnerable core, phases, hits, and defeat; plus map route/reveal/world-completion presentation. Existing boss telegraphs, HUD warnings, sprites, and geometry remain readable with optional effects disabled.

At most 600 particles are active. `AMBIENT`, `NORMAL`, and `CRITICAL` priorities drop lower-value work first under load; effect definitions also impose local caps. Continuous emitters have explicit owners and are cleared on F7, life/boss resets, level loads, map transitions, and shutdown. Full, reduced, and optional-off quality modes are supported; debug `F6` toggles optional effects. The debug panel reports total particles, emitters, ambient/gameplay counts, and screen effects. Save schema remains version 2 and contains no transient effect state.

Run repeatable 600-frame performance scenarios with:

```bash
python tools/effects_benchmark.py normal
python tools/effects_benchmark.py stress
python tools/effects_benchmark.py phase3
python tools/effects_benchmark.py defeat
```

See [docs/EFFECTS_SYSTEM.md](docs/EFFECTS_SYSTEM.md) for architecture, authoring rules, integration contracts, reset policy, quality behavior, test coverage, and benchmark results.


## Audio, music, and ambience

Phase 16 routes gameplay outcomes into stable audio IDs managed by one optional `AudioManager`. Independent Master, Music, SFX, Ambience, UI, and future Voice buses support clamped runtime volumes and mute. Sounds are lazily cached, missing assets log once, repeated cues use cooldowns and instance caps, and important cues receive channel priority. World sounds support lightweight stereo panning.

Music contexts cover the World Map, Verdant levels, Emberfall Ravine, ruins, Ashen Warden, and World Complete. Explicitly owned ambience covers Verdant wind, canopy, ravine, ruins, and Sanctum. F7, replay, life/boss reset, transitions, and shutdown rebuild one correct context without leaking loops. Debug `F8` toggles mute. Campaign saves remain schema 2 and contain no playback state or audio preferences.

All 58 placeholder WAVs are original deterministic tones/noise generated by `tools/generate_placeholder_audio.py`; no external audio was downloaded. See [docs/AUDIO_SYSTEM.md](docs/AUDIO_SYSTEM.md) and [docs/AUDIO_CATALOG.md](docs/AUDIO_CATALOG.md).


## Front-end, settings, pause, and Game Over

Phase 17 provides a normal title flow with Continue, New Game, three save slots, Settings, Credits, and Quit. Slot recovery/corruption/version states are presented safely; overwrite and delete actions require confirmation. See [docs/MENU_SYSTEM.md](docs/MENU_SYSTEM.md).

Application settings are independent from campaign saves and persist Master/Music/SFX/Ambience/UI volume, mute, effects quality, and fullscreen. Settings apply immediately and can be reset without touching campaign data. See [docs/SETTINGS_SYSTEM.md](docs/SETTINGS_SYSTEM.md).

Pause freezes the complete gameplay simulation and offers Resume, Settings, Restart, World Map, and Main Menu. Losing the final life after Nova's death animation opens Game Over; Retry rebuilds a fresh authored level, including a full-health Phase 1 boss, without awarding failed-run progression. See [docs/GAME_OVER.md](docs/GAME_OVER.md).


## Controller support

Phase 18 adds full single-player gamepad support without changing keyboard controls. Left stick/D-pad move and navigate; south face jumps/confirms; west face attacks; north face interacts; east face backs out; Start pauses. Prompts switch automatically between keyboard and controller. Controllers may be connected or removed while running, and vibration can be disabled in Settings. See [docs/INPUT_SYSTEM.md](docs/INPUT_SYSTEM.md) and [docs/CONTROLLER_SUPPORT.md](docs/CONTROLLER_SUPPORT.md).
