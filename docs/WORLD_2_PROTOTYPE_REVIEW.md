# World 2 Ember Current Prototype Review

## Recommendation

**READY WITH REVISIONS.** The mechanic is technically viable and supports the Glassreach theme, but subjective feel, strength tuning, projectile-route clarity, and production presentation require human playtesting before full World 2 production.

| Objective | Result | Evidence |
|---|---|---|
| World 2 identity | PROMISING | A distinct spatial rule and energy-flow vocabulary; final art is absent. |
| Momentum | STRONG | Acceleration rewards flow while preserving counter-steering. |
| Environmental interaction | PROMISING | Collision/platform riding remain authoritative; platform bodies are not Current-driven. |
| Mechanical combination | STRONG | Graybox combines jumps, power-ups, moving platforms, combat, and overlaps. |
| Projectile puzzles | PROMISING | Pulse bends without losing collision/lifetime; human readability evidence is pending. |
| Traversal | STRONG | Horizontal, lift, diagonal, and overlapping flows share one rule. |
| Combat | PROMISING | One opted-in flyer proves clean integration. |
| Secrets | PROMISING | Optional vector routes are possible; production secrets were excluded. |

## Graybox and findings

`prototype_glassreach_currents` is a noncanonical developer-only 98×16-tile laboratory targeting 3–6 minutes. It is not registered in campaign or World Map. Its seven demonstrations are horizontal counter-steering, vertical lift/Aether Wing, diagonal Pulse routing toward a breakable target, moving-platform riding, an opted-in flyer, additive overlap, and a strong-current finish. One checkpoint shortens testing.

The optional field gives World 1 effectively zero Current-query work; force addition is deterministic; collision remains authoritative; projectile safety survives; effects-off communication is structural; editor/debug workflows reuse existing architecture; no save, achievement, or campaign schema changed. Weaknesses are placeholder art, no feathered boundary blend, a read-only editor inspector, and switch/reversal APIs that are debug/runtime-only rather than authored links.

## Human playtest checklist

Do not fabricate answers. Ask whether counter-pushing is interesting, direction and strength are immediately legible, projectile bending is intentional, vertical lift is controllable, Wind Boots and Aether Wing remain useful, platform/enemy combinations feel fair, and the final room feels like World 2 rather than World 1 with wind.

## Luminous Sentinel implications

Currents could telegraph arena lanes, bend readable boss projectiles, or create recovery lifts. A future boss must not combine opaque overlap, forced motion, and unavoidable damage. No Sentinel behavior is approved or implemented here.
