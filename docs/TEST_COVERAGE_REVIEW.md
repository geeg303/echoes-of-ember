# Phase 24 Test Coverage Review

## Baseline and final scope

Phase 24 began with 312 passing tests in 14.74 seconds. The expanded standard suite has 384 passing tests in 19.30 seconds. `coverage.py` was not installed, and Phase 24 deliberately avoided adding a dependency merely to optimize a percentage. This review is risk-based and behavioral.

Strong coverage exists for player movement/collision at multiple `dt` values, combat, four power-ups, five enemy archetypes, moving/falling/disappearing platforms, switches, doors, checkpoints, breakables and terrain-cache invalidation, collectibles, level completion, World Map graph/progression, secrets, Ashen Warden states/phases/attacks/defeat, Pause, Game Over, save recovery/migrations, settings migration/fallback, achievement persistence and all 19 definitions, dialogue/NPC selection and graph integrity, keyboard/controller equivalence, audio/effects lifecycle, editor round trips/playtest isolation, debug isolation, performance cache bounds, and no normal-frame disk reads.

Flagship scenarios now prove:

- World 1 progression survives a save/load boundary after every stage;
- boss defeat is required for authoritative world completion;
- the Ember Veil branch remains revealed after a normal replay and reload;
- all 12 authored secrets aggregate without replay duplication;
- every dialogue node is reachable and can reach a terminal;
- every achievement definition is satisfiable and unlockable;
- all supported launch modes exit successfully and invalid combinations fail cleanly;
- repeated runtime reconstruction does not accumulate entities, projectiles, effects emitters, or NPCs.

## Bugs found and protected

Phase 24 found grounded-state flicker at high update rates when sub-pixel gravity rounded Nova's collision rectangle to exact floor contact. Collision now performs a one-pixel support query after movement; bounce pads remain excluded. A multi-`dt` regression test protects the behavior.

CLI testing also found conflicting editor/save and direct-level/save flags were silently accepted, while malformed editor IDs could expose an exception. `main.py` now returns a clear exit code 2 without a traceback, protected by process-level tests.

## Mutation-like review

Critical assertions were reviewed around save migration, boss completion, secret monotonicity, achievement idempotence, persistence isolation, and cache invalidation. Inverting their governing conditions would change an asserted public result. Existing private-member assertions remain only where the private value itself is the explicit bounded-cache diagnostic contract.

## Remaining automated gaps

Automation does not prove pixel-art quality, animation appeal, collision *feel*, camera comfort, perceived audio balance, music quality, real controller mappings across every vendor/OS, vibration strength, fullscreen/vsync behavior, accessibility comfort, editor mouse ergonomics, dialogue pacing, or performance under a real compositor. Rare OS-level power loss during filesystem replacement is simulated only at API boundaries. The game remains effectively single-threaded, so concurrency testing is intentionally absent.

These items form the Phase 25 human test matrix: complete keyboard and controller playthroughs, multiple display modes, actual audio hardware/mute transitions, visual readability at every effects quality, editor mouse workflows, dialogue pacing, accessibility review, and representative Windows/Linux/macOS performance.

