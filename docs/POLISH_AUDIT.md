# Phase 25 Initial Polish Audit

The audit began from commit `01ea9fe` with a clean synchronized worktree. Quick verification passed in 19.90 seconds, full verification passed in 30.39 seconds, and all 384 tests passed. Every measured p95 remained below the 16.67 ms target. Review combined code/data inspection, automated state construction, headless rendering, and existing behavior tests. Subjective audio, physical-controller, and real-display claims are deliberately excluded.

## Findings

| Severity | Category | Finding | Decision |
|---|---|---|---|
| P0 | — | No blocker found. | — |
| P1 | UX / visual | The 11-row Settings menu overflows its generic menu panel and footer at 1280×720. | Fix with adaptive dense layout and structural tests. |
| P1 | accessibility / camera | Effects quality `Off` suppresses particles but not camera shake, so the existing accessibility control does not fully reduce motion. | Make Reduced scale shake and Off suppress it; retain settings schema 2. |
| P1 | UX | Level Complete contains obsolete “Campaign progression coming later” copy despite the working World Map. | Remove stale branch and keep current dynamic prompts. |
| P2 | accessibility / World Map | Node state is communicated mainly by color and radius; locked/completed/mastered states need shape or glyph redundancy. | Add lock, check, star, boss, secret, and goal markers. |
| P2 | UX / Pause / Game Over | Pause and Game Over panels sit directly over the last gameplay frame without a consistent dim treatment. | Add reusable screen dimming before the menu panel. |
| P2 | visual language | Common colors, safe margins, panels, and dimming are repeated as literals across player-facing screens. | Add a small `ui.style` module; do not build a theme framework. |
| P2 | save slots | Slot state details are terse and slot-action heading is generic. | Improve screen title and status wording without changing save semantics. |
| P2 | feedback | Camera shake requests use a useful intensity hierarchy but quality/accessibility behavior is undocumented and untested. | Document and test Full/Reduced/Off behavior. |
| P2 | level readability | Authored validators prove safe spawns, goals, references, and paths; subjective hazard contrast and pacing still need real playtesting. | Preserve data; record human review. |
| P3 | achievements | Browser is structurally bounded and hidden entries are protected, but physical controller scroll feel remains subjective. | Human review. |
| P3 | audio | Bus defaults, priorities, caps, and transitions are structurally sound. Relative loudness and clipping cannot be judged headlessly. | Human listening pass. |
| P3 | narrative | All dialogue graphs terminate and text is within authored limits. Voice, pacing, and exposition remain subjective. | Human reading/play pass. |
| P3 | editor | Layout, isolation, cache, pan/zoom, and commands are automated; mouse ergonomics are not. | Human review. |

## Scope guard

No movement, enemy, power-up, level-layout, save, achievement, editor, or debug redesign is justified. Phase 25 changes should remain presentation-only except for genuine defects with regression tests. Campaign/save schema remains 3, application settings remains 2, and achievement profile remains 1.
