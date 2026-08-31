# Particle and Visual Effects System

## Purpose and authority boundary

Phase 15 adds presentation polish without changing gameplay. `EffectsSystem` observes completed gameplay events; particles never decide hits, movement, damage, boss phases, unlocks, score, or saves. Base sprites, arena markings, HUD warnings, door/platform states, and boss telegraphs remain authoritative and visible when optional effects are off. No gameplay hit-stop was introduced.

## Architecture

- `effects/particle.py` defines a lightweight delta-time `Particle` with position, velocity, acceleration, lifetime, size/alpha interpolation, rotation, drag, render space, priority, and effect ID.
- `effects/definitions.py` is the typed procedural catalog. Every definition selects a circle, spark, rectangle fragment, glow, or dust primitive and fixed bounded ranges.
- `systems/effects_system.py` owns all live particles, emitter registrations, flashes, quality state, deterministic random generation, caps, culling, shared alpha surfaces, update, draw, and cleanup.
- Gameplay managers publish or expose visual outcomes. The Game boundary translates them into effect IDs; gameplay systems never inspect particle state. Projectile terrain/destruction events use a typed `ProjectileEffectEvent` queue.

World-space effects retain world coordinates and receive a camera offset only while drawing. Screen-space map effects and flashes never receive a camera transform. Effect randomization uses a dedicated seeded `random.Random`, never the gameplay RNG.

## Lifecycle and capacity

The global cap is 600 particles. Each definition also has a local maximum. Priorities are `AMBIENT`, `NORMAL`, and `CRITICAL`; a critical request may evict ambient or normal particles, while an ambient request is dropped when full. Reduced quality halves noncritical burst counts and emitter rates. Optional-off suppresses ambient and normal particles while retaining bounded critical feedback; every required telegraph exists outside this layer.

Particles use seconds, update with `dt`, and always have finite lifetimes. Continuous emitters require an explicit owner ID. Ambient regions only emit inside a padded camera viewport. Rendering is culled with a padded viewport and reuses one alpha surface per canvas size.

`clear()` removes particles, emitters, flashes, and pending shake requests. It is used by F7/replay, level construction, map/level transitions, and relevant respawn or boss resets. Level ambience and checkpoint/boss-owned emitters are rebuilt only from current authoritative runtime state. Nothing is serialized; save schema remains version 2.

## Integration catalog

Player events include jump/landing dust, Aether Wing double-jump flare, damage sparks/flash, and death burst. Power-up feedback covers Ember Pulse, Wind Boots trails, Aether Wing, Stone Guard activation and shield break. Combat covers pulse launch/trail/impact, enemy hit/defeat, stomp impact, and armor resistance.

World feedback covers each collectible tier, checkpoint activation and idle glow, secret discovery and challenge completion, breakable destruction, switches, doors, and warning dust. Verdant levels choose viewport-aware leaves, pollen, embers, ruins dust, or sanctum motes. Ashen Warden definitions cover awakening, slam, bolts, leaps, phase transitions, vulnerable core, core impacts/bursts, and defeat. Screen-space definitions cover route unlocks, Ember Veil reveal, Sanctum availability, and world completion.

Screen flash opacity is clamped to 112 and durations are brief. Shake callers submit requests; the manager combines them into one bounded camera request each frame, preventing stacking.

## Authoring an effect

1. Add one unique `EffectDefinition` in `effects/definitions.py`.
2. Choose `WORLD` or `SCREEN` space and the lowest suitable priority.
3. Keep count, lifetime, speed, size, and local maximum conservative.
4. For continuous effects, give it an emission rate and register it with a stable owner via `start_emitter`. Stop it when the authoritative owner ends.
5. Trigger the effect only after the gameplay event succeeds. Do not read particles to make a gameplay decision.
6. Ensure the mechanic stays readable in optional-off mode.
7. Add deterministic lifecycle/cap/integration tests and run all benchmarks.

## Debugging and quality

With `DEBUG_MODE`, F6 toggles optional effects between Full and Off. `EffectQuality.REDUCED` is available to future settings UI. The debug overlay shows total particles, emitter count, ambient/gameplay counts, and screen effects. F7 performs a full authored reset and reconstructs only appropriate ambient emitters.

## Automated validation

Phase 15 tests cover deterministic spawning, delta-time motion, interpolation, expiry, unknown IDs, per-effect/global caps, priority eviction, reduced/off quality, emitter ownership and stopping, flash limits, combined shake, coordinate separation, definitions, level/map transitions, F7 reconstruction, 30-second leak behavior, and save isolation. The complete suite passes 193 tests.

## Performance results

All numbers are 600 frames at 1280×720 in the headless development environment.

| Scenario | Mean | p95 | Max | Peak particles | Emitters |
|---|---:|---:|---:|---:|---:|
| Normal ambient/gameplay effects | 2.539 ms | 3.254 ms | 4.451 ms | 38 | 2 |
| Stress combat effects | 4.137 ms | 4.765 ms | 6.986 ms | 209 | 2 |
| Boss phase-three effects | 2.907 ms | 3.810 ms | 5.669 ms | 107 | 1 |
| Boss defeat effects | 2.460 ms | 3.184 ms | 5.462 ms | 51 | 1 |
| Integrated boss gameplay after Phase 15 | 9.018 ms | 9.852 ms | 28.084 ms | 41 | 2 |

The recorded comparable pre-effects boss benchmark was 6.260 ms mean, 6.846 ms p95, and 17.057 ms max. Phase 15 adds about 2.758 ms mean while keeping p95 comfortably below the 16.67 ms 60 FPS frame budget. The isolated stress benchmark also remains below budget.

## Intentional limitations

Effects remain procedural placeholders and sound assets remain absent. Quality selection is currently a programmatic/debug facility rather than a finished settings menu. Map celebration events are lightweight because persistent animation choreography and the full audio pass belong to later phases.
