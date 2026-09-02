# Phase 23 Performance Optimization

## Scope and method

Phase 23 retained six low-risk changes selected from the Phase 23A profile. Measurements use Python 3.14.6, pygame-ce 2.5.8, dummy SDL audio/video, the 1280×720 internal canvas, fixed 1/60-second updates, and 600 frames per scenario. They are same-host comparisons rather than hardware-independent claims. See `PERFORMANCE_BASELINE.md` for the original profile and rejected speculative work.

Run the suite with:

```bash
python -m tools.performance_benchmark --all --frames 600 --output results.json
python -m tools.debug_benchmark off --frames 600
python -m tools.soak_test --frames 18000 --draw-every 30
```

## Before and after

| Scenario | Baseline mean / p95 | Optimized mean / p95 | Mean change | Post spikes >16.67 / >25 / >33.3 ms |
|---|---:|---:|---:|---:|
| Quiet — Verdant Beginning | 10.102 / 10.919 ms | 7.141 / 7.833 ms | -29.3% | 1 / 1 / 0 |
| Busy — Verdant Ruins | 10.006 / 10.828 ms | 7.240 / 8.646 ms | -27.6% | 1 / 0 / 0 |
| Ashen Warden | 8.581 / 9.455 ms | 6.535 / 7.883 ms | -23.8% | 1 / 1 / 0 |
| Warden Phase 3 | 8.479 / 9.325 ms | 6.749 / 8.456 ms | -20.4% | 1 / 1 / 0 |
| Boss defeat burst | 8.474 / 9.310 ms | 6.681 / 7.711 ms | -21.2% | 1 / 0 / 0 |
| Effects stress | 8.448 / 9.338 ms | 5.690 / 7.005 ms | -32.6% | 1 / 1 / 0 |
| Verdant Ruins editor | 5.369 / 5.923 ms | 5.808 / 6.769 ms | +8.2% | 0 / 0 / 0 |

The editor result is within host-run variance and remains far below budget; the grid cache specifically removes repeated full document reconstruction, covered by a deterministic invariant test. Isolated maximum frames vary with startup, SDL, and host scheduling and are not treated as evidence of a gameplay regression. Post-change p95 remains below the 16.67 ms target in every scenario.

## Retained optimizations

### Native-size presentation

- Hotspot: `pygame.transform.scale` consumed about 0.435 seconds in the 300-frame profile even when source and destination were both 1280×720.
- Change: `Game._present()` blits directly at native size and scales only when the actual window size differs.
- Risk: alternate resolutions or fullscreen could skip required scaling.
- Regression coverage: a same-size presentation test spies on `pygame.transform.scale`; startup/settings tests cover normal display construction.
- Result: contributes to the 20–33% runtime scenario improvements; the transform is absent from the native-size path.

### Static terrain chunks

- Hotspot: tile rendering consumed about 0.468 seconds and issued roughly 15,600 primitive tile draws over 300 boss frames.
- Change: visible terrain is rendered from lazy 16×8-tile alpha chunks. The finite level dimensions provide a natural hard cache bound. Destroying a breakable invalidates only its containing chunk.
- Risk: stale visuals after runtime tile mutation or incorrect viewport edges.
- Regression coverage: chunk reuse/bounds, targeted invalidation, breakable collision, level rendering, and full gameplay tests.
- Result: repeated visible tiles become a handful of surface blits; collision data and query behavior are unchanged.

### Background gradient cache

- Hotspot: rebuilding the unchanged four-pixel-band gradient consumed about 0.378 seconds in the profile.
- Change: build it once per output size and reuse the surface.
- Risk: stale background after a resolution change.
- Regression coverage: cache identity/rebuild test plus startup and rendering smoke tests.
- Result: preserves procedural parallax while removing repeated gradient construction.

### Empty screen-effects fast path

- Hotspot: the screen-effects pass cleared and composited a 1280×720 alpha surface even when no screen particle or flash existed.
- Change: return immediately when that pass has no work. World effects are unaffected.
- Risk: incorrectly skipping a live screen effect.
- Regression coverage: explicit empty-pass test and the complete effects lifecycle suite.
- Result: largest relative improvement appears in the effects scenario, whose mean fell from 8.448 to 5.690 ms.

### Bounded HUD surface caches

- Hotspot: unchanged labels, counts, and four panel surfaces were recreated every frame.
- Change: cache panels by size/alpha and text by font identity/text/color. Text uses a 96-entry LRU bound; panels use a 16-entry bound.
- Risk: unbounded dynamic score/count strings or visually stale dynamic content.
- Regression coverage: bounds, eviction, panel reuse, HUD behavior, health, score, and power-up tests.
- Result: stable presentation work is reused while animated scaling and live values remain correct.

### Editor grid cache

- Hotspot: the editor rebuilt a dense tile grid from serialized tile records during repeated draws.
- Change: cache the authoritative derived grid; copy/update it during tile mutations and invalidate it on document restore.
- Risk: stale editor state after undo/redo or edits.
- Regression coverage: rebuild-on-mutation invariant plus editor undo/redo, round-trip, validation, and playtest-isolation tests.
- Result: repeated viewport rendering no longer reconstructs the complete level grid.

## Systems intentionally unchanged

Collision candidate queries, enemy AI activation, boss logic, projectile cleanup, audio ownership, particle lifecycle/caps, NPCs, dialogue, achievements, input, and saves were already minor in the profile or already bounded. ECS conversion, pools, global GC manipulation, full-world render surfaces, broad spatial partitioning, and gameplay simulation changes were rejected as unjustified complexity.

No hot-path file or JSON reads were found in runtime update/draw code. Assets, level JSON, dialogue, saves, settings, and achievement data remain lifecycle-bound operations. Fonts are created during construction and HUD glyph surfaces are now bounded and reused.

## Stress and memory result

The repeatable 18,000-frame boss soak (draw every 30 simulation frames) completed in 21.491 seconds without a crash. After warm-up, traced live memory changed by -936 bytes; peak traced memory was 43,089 bytes. It ended with 8 particles, 0 projectiles, 0 debug events, 18 bounded audio events, 0 achievement toasts, and 4 cached terrain chunks against a natural maximum of 6. This test supplements rather than replaces interactive playtesting.

## Remaining bottlenecks and next steps

Procedural parallax layers, active effect drawing, debug overlays, and general Pygame software composition remain the largest expected render costs. They currently meet the 60 FPS headless target and should not receive speculative redesign. Phase 24 should expand deterministic non-visual regression coverage and preserve the benchmark/invariant suite. Phase 25 should include a real-display review on representative Windows, Linux, and macOS hardware, since dummy SDL cannot measure compositor, vsync, input latency, GPU/driver, or real audio behavior.

Phase 24 preserved the benchmark envelope and added verification-runner integration. Cache bounds, breakable invalidation, native-size presentation, editor grid reuse, empty effects, no-frame-disk-I/O, 3,000-frame full-verification soak, and 18,000-frame release soak remain deterministic gates; machine-sensitive timing figures remain informational.

## Phase 25 regression check

The final same-host 600-frame pass recorded mean/p95 values of 7.077/7.897 ms quiet, 7.055/8.010 ms busy, 6.329/7.377 ms boss, 6.356/7.312 ms boss phase 3, 6.381/7.369 ms boss defeat, 5.608/6.433 ms effects stress, and 5.574/6.236 ms editor. Every p95 remains comfortably below 16.67 ms. Release verification, including the 18,000-frame soak, passed in 78.789 seconds.
