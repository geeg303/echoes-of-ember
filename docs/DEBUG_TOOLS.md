# Developer Debug Tools

Phase 22 provides a developer-only diagnostics layer. It is disabled during ordinary launches and adds no persistent schema.

## Launching

```bash
python main.py --debug
python main.py --debug --level verdant_03
python main.py --debug --slot 1
python main.py --editor --debug --level verdant_03
```

Debug slot launches load the selected slot for inspection but suppress campaign autosaves and profile achievement writes. `--debug --new-game` is rejected. Editor playtests remain temporary and isolated; `Shift+F5` starts a debug playtest while `F5` remains the normal playtest.

## Architecture and safety

`DebugManager` owns developer hotkeys, transient state, command dispatch, selection, and exports. `build_snapshot()` extracts immutable primitive mappings from authoritative game state. The overlay and exports consume that snapshot rather than retaining live objects. The explicit `DebugCommandRegistry` parses with `shlex`, validates arguments and contexts, and never evaluates Python. Mutations call game or subsystem APIs. A gameplay mutation taints the current debug run, but all debug sessions are nonpersistent regardless of taint.

The profiler stores at most 120 samples per metric and 20 frame spikes. Semantic event history is limited to 50 entries, command history to 50, and output to seven lines. Nothing writes per frame.

## Hotkeys

| Key | Action |
|---|---|
| F1 | Toggle master overlay |
| F2 / Shift+F2 | Next / previous page |
| F3 | Toggle collision visualization |
| F4 | Toggle authored trigger visualization |
| F6 | Cycle optional effect quality (legacy development shortcut) |
| F7 | Reconstruct the current level runtime |
| F8 | Toggle debug simulation pause |
| F9 | Advance one simulation update while debug-paused |
| F10 | Toggle bounded free inspection camera |
| Backtick | Open/close command palette |
| Mouse 1 | Select an overlapping runtime object for read-only inspection |

Free-camera movement uses WASD or arrows and never moves Nova. Palette typing consumes gameplay input, so typed attack/jump keys do not leak into the simulation. Up/Down recalls bounded command history; Escape closes the palette.

## Overlay pages

The pages are Summary, Player, World, Entities, Boss, Input, Audio, Effects, Progression, and Performance. Summary is intentionally compact. Detailed pages expose actual runtime names and safe primitive values. The performance page reports current, mean, p95, and maximum values plus bounded spike counts at 16.67, 25, and 33.3 ms.

## Visualizations and inspector

Collision mode outlines nearby terrain, hazards, player, enemies, projectiles, and doors. Trigger mode shows checkpoints, switches, secrets, NPC interaction radii, goals, platform paths, boss trigger/arena, and viewport boundary. Entity labels include enemy health and projectile faction/lifetime. Rendering is read-only and uses world coordinates plus the active render offset.

Click selection uses a deterministic priority: boss, enemy, NPC, projectile, platform, door, switch, checkpoint, then player. The inspector holds copied primitive details only.

## Simulation tools

Debug pause freezes authoritative gameplay updates while rendering and debug UI continue. Frame step advances exactly one bounded update then remains paused. Supported time scales are 0.25x, 0.5x, 1x, and 2x. Free camera has authored-world bounds and does not alter the authoritative gameplay camera or player.

## Events, profiling, and exports

The event trace records bounded semantic diagnostics. `repro` creates a unique JSON file under `debug_output/` with snapshot primitives, recent events, profiler data, and debug toggles. `perf export` writes bounded performance JSON. `screenshot` stores the internal frame under `debug_output/screenshots/`. These exports never overwrite saves and serialize no executable objects.

## Limitations

- The inspector is read-only and does not cycle overlapping candidates.
- Subsystem profiling currently measures total update/render/frame cost rather than every individual manager.
- Free camera uses keyboard input only.
- Deterministic replay, remote debugging, telemetry, crash reporting, and arbitrary scripting are intentionally absent.
- Debug changes never produce campaign completion or achievement persistence; use a normal session for genuine progression verification.

See [DEBUG_COMMANDS.md](DEBUG_COMMANDS.md) for the complete command catalog.

## Phase 23 performance checks

The rolling profiler remains bounded at 120 samples per metric and 20 spike records. Use `python -m tools.debug_benchmark MODE --frames 600` for `off`, `summary`, `collision`, `triggers`, or `performance`. These modes intentionally exercise the real debug drawing path; see `PERFORMANCE_OPTIMIZATION.md` for current measurements and environment caveats.
