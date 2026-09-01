# Phase 23A Performance Baseline

## Method

Measurements use Python 3.14.6, pygame-ce 2.5.8, dummy SDL audio/video, the 1280×720 internal resolution, deterministic fixed 1/60-second updates, and 600 measured frames per scenario. Headless numbers are useful only for same-host comparisons; they are not claims about every real display or computer. Memory tracing is run separately because `tracemalloc` materially changes timing.

`python -m tools.performance_benchmark --all --frames 600 --output baseline.json` covers quiet gameplay, a busy normal level, integrated boss activity, forced Phase 3, a defeat burst, effects stress, and editor pan/render. The older Phase 22 debug benchmark remains the comparison tool for overlay modes.

## Phase 23A baseline

| Scenario | Mean | Median | p95 | p99 | Maximum | Spikes >16.67 / >25 / >33.3 ms |
|---|---:|---:|---:|---:|---:|---:|
| Quiet — Verdant Beginning | 10.102 | 10.099 | 10.919 | 11.715 | 19.563 | 1 / 0 / 0 |
| Busy — Verdant Ruins | 10.006 | 10.017 | 10.828 | 11.355 | 17.614 | 1 / 0 / 0 |
| Ashen Warden | 8.581 | 8.621 | 9.455 | 9.965 | 17.522 | 1 / 0 / 0 |
| Warden Phase 3 | 8.479 | 8.572 | 9.325 | 10.089 | 18.264 | 1 / 0 / 0 |
| Boss defeat burst | 8.474 | 8.606 | 9.310 | 9.890 | 16.266 | 0 / 0 / 0 |
| Effects stress | 8.448 | 8.483 | 9.338 | 10.167 | 14.649 | 0 / 0 / 0 |
| Verdant Ruins editor | 5.369 | 5.348 | 5.923 | 6.190 | 10.190 | 0 / 0 / 0 |

Separate Phase 22 debug benchmark rerun:

| Mode | Mean | p95 | Maximum |
|---|---:|---:|---:|
| Off | 10.028 | 14.081 | 29.239 |
| Summary | 10.543 | 13.141 | 35.318 |
| Collision | 10.236 | 11.239 | 31.665 |
| Triggers | 9.799 | 10.578 | 29.641 |
| Performance | 9.644 | 10.435 | 28.494 |

The debug samples include natural host variance and should not be compared across modes as if they were a deterministic microbenchmark. The primary requirement—debug-off p95 below 16.67 ms—passes.

## CPU profile evidence

A 300-frame integrated boss `cProfile` run recorded approximately 3.14 seconds in `Game.draw()` versus 0.255 seconds in `Game.update()`. The largest actionable cumulative render costs were:

1. Procedural background: 0.786 seconds, including 0.378 seconds rebuilding an unchanged gradient.
2. Tile rendering: 0.468 seconds and roughly 15,600 `draw_tile` calls.
3. Final `pygame.transform.scale`: 0.435 seconds despite equal internal/window sizes in the benchmark.
4. World/screen effects drawing: about 0.87 seconds combined; the empty screen-effect pass still cleared and blitted a full-resolution alpha surface.
5. HUD: 0.211 seconds, including four temporary panel surfaces and repeated unchanged text renders per frame.

Collision, player update, enemy update, boss update, projectiles, camera, audio, and achievement dispatch were each small. No spatial-partitioning or gameplay-loop rewrite is justified by this profile.

## Ranked changes

| Rank | Candidate | Expected benefit | Risk |
|---|---|---|---|
| 1 | Skip final scaling when display size already equals internal size | High, direct removal of measured transform | Very low |
| 2 | Cache static background gradient | Medium | Very low |
| 3 | Lazily cache finite static terrain chunks and invalidate breakable chunks | High | Medium; requires invalidation tests |
| 4 | Skip empty screen-effect overlay pass | Medium | Low |
| 5 | Bound/cache HUD panel and stable text surfaces | Small–medium | Low |
| 6 | Cache editor tile-grid reconstruction until terrain changes | Small | Low |

Rejected before implementation: entity ECS conversion, projectile pooling, broad collision partitioning, enemy simulation changes, global GC changes, particle pooling, full-world terrain surfaces, and NPC spatial indexing. The profile does not justify their complexity or semantic risk.
