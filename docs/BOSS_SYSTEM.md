# Boss System

Phase 14 adds reusable, data-driven boss encounters without placing attack logic in `Game`.

## Architecture

- `bosses/boss_base.py` owns typed configuration, health, phases, vulnerability, invulnerability, state transitions, reset, one-time defeat, and one-time score claiming.
- `bosses/ashen_warden.py` owns one boss's deterministic attack selection, movement, attack execution, and procedural art.
- `systems/boss_system.py` coordinates the boss with the shared projectile manager, player damage contract, arena, score, effects hooks, and HUD data.
- `world/boss_arena.py` owns the authored trigger, arena bounds, linked doors, completion, reset, and camera-bound data.
- `ui/boss_hud.py` renders screen-space boss name, segmented health, phase, and intro title. It never mutates encounter state.

Boss states are `INTRO`, `IDLE`, `MOVE`, `TELEGRAPH`, `ATTACK`, `RECOVER`, `STAGGERED`, `PHASE_TRANSITION`, and `DEFEATED`. Bosses may define any number of ordered phases. Health thresholds and attack pools live in validated configuration rather than gameplay code.

## Combat contracts

Player Ember Pulse projectiles remain `Faction.PLAYER`; boss projectiles use the existing `Faction.ENEMY` projectile class and carry the boss ID as `owner_id`. Damage is accepted only during explicit vulnerability windows and observes a short boss hit-invulnerability interval. Major attacks always pass through telegraph, action, and recovery states. Ember Rain and leap attacks add arena-space warning markers before danger appears.

Boss contact and projectiles call `Player.apply_damage`, so ordinary hurt invulnerability, knockback, lives, and Stone Guard remain authoritative. Stone Guard absorbs exactly one event. Phase transitions and intros disable contact damage. A lethal valid boss hit takes precedence over a simultaneous player death; Nova is stabilized with one health during the committed defeat sequence.

## Arena lifecycle

A level may contain one validated `boss_encounter` definition:

```json
{
  "boss_encounter": {
    "boss_id": "ashen_warden",
    "boss_spawn": [1680, 636],
    "arena_bounds": [448, 128, 1712, 640],
    "trigger_bounds": [505, 350, 110, 418],
    "door_ids": ["arena_entry_door", "arena_exit_door"],
    "pulse_source": [620, 690]
  }
}
```

The boss ID must have a valid file in `data/bosses`, the spawn and trigger must be inside valid arena bounds, all referenced IDs must be authored doors, and the level must contain a checkpoint and Ember Pulse pickup. Crossing the trigger closes the doors, starts the intro, locks the camera to reusable arena bounds, and grants an encounter-scoped Ember Pulse capability. The capability remains even when a normal timed pickup expires and is cleared on encounter reset or completion.

Losing a life resets boss health, phase, attack history, hazards/projectiles, arena doors, HUD state, and encounter ability. F7 reconstructs the entire level runtime using the same load path. Boss defeat clears hostile projectiles, opens doors after the defeat sequence, creates a normal `LevelResult`, records a monotonic boss flag, and autosaves. Replays create fresh encounters but cannot erase boss/world completion; abandoning a replay creates no replacement result.

## Boss configuration

Configuration validates non-empty IDs/names, positive health/damage/reward/size, finite timings and movement values, consecutive phase numbers, unique descending thresholds, and non-empty unique attack pools. It is loaded once when the boss runtime is constructed.

To author a future boss:

1. Add and validate its JSON configuration in `data/bosses`.
2. Implement a `Boss` subclass that selects attacks and emits shared projectiles.
3. Register the implementation in the boss factory/orchestrator.
4. Author a short level with safe spawn, checkpoint, attack source, doors, arena, trigger, and goal metadata.
5. Add a `boss` World Map node with stable `level_id` and `boss_id`.
6. Add progression, reset, persistence, telegraph, and softlock tests.

Optional sound hooks currently resolve through silent asset fallbacks: awaken, slam, projectile, phase, hurt, and defeat. Lightweight shake and combat effects are used; the full particle and audio phases remain deferred.

## Audio integration

Boss systems emit attack/state event names; `Game` translates them to catalog IDs and `AudioManager` plays them. Boss AI never reads playback state. The dedicated track starts once at encounter activation, phase changes use stingers without restarting music, life/reset cleanup prevents duplicate loops, and defeat fades music while visuals remain authoritative when muted.

## Game Over contract

Final-life death waits for Nova's death animation, then clears boss projectiles, vulnerability emitters, arena camera bounds, transient effects, and encounter audio without awarding defeat. Retry reconstructs the encounter at full health in Phase 1; World Map/Main Menu preserve only progress committed before the failed attempt.

## Controller input and vibration

The Ashen Warden receives only logical movement/jump/attack/pause input. South face skips the intro through Confirm, west face uses the normal Ember Pulse contract, and all phases remain governed by existing AI/combat systems. Central vibration covers damage, ground slam, phase transitions, and defeat; unsupported or disabled rumble is a safe no-op.

## Achievement observation

Committed Ashen Warden defeat and subsequent authoritative world completion emit separate semantic events. Their queued toasts wait until the defeat/completion presentation is clear. Boss behavior never reads achievement state.

## Editor support

Boss levels round-trip without metadata loss. Arena, trigger, doors, spawn, and pulse source remain validated; boss AI graph authoring is intentionally excluded.
# Debug diagnostics

The Boss page exposes health, phase, state/timer, attack, vulnerability, arena lock, and defeat state. `boss damage` routes through `BossSystem.debug_damage()` to preserve phase and defeat invariants; `boss reset` uses the existing encounter reset contract. Debug boss results never persist.

## Phase 23 performance review

Ashen Warden activation, Phase 3, and defeat-burst scenarios are part of the repeatable performance suite. Boss update logic was not a measured hotspot and remains unchanged; optimization focuses on shared rendering paths. Post-optimization boss p95 is 7.883 ms, Phase 3 p95 is 8.456 ms, and the defeat-burst p95 is 7.711 ms in the documented headless environment.

Phase 24 keeps the full boss state/phase/attack, vulnerability, one-time score, projectile cleanup, controller-only victory, Game Over retry, save restoration, achievement, effects, audio, debug-isolation, performance, and long-soak matrix in standard or release verification.
