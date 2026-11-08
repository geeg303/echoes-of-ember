# Content Production Roadmap

This roadmap begins after the completed technical/World 1 Phases 0–26. Milestones are outcome gates, not automatic feature authorization. Each ends with content validation, relevant regression/scenario tests, performance review, documentation, and a stable commit.

| Milestone | Outcome | Exit criteria |
|---|---|---|
| A — Game & Content Bible | Coherent full-game direction | Canon/proposals separated; Worlds 2–4 and cross-game arcs documented |
| B — World 2 Prototype | Prove Ember Currents and Glassreach language | One graybox test slice; editor/debug/validator support; no campaign expansion yet unless explicitly approved |
| C — World 2 Full Production | Author five intentional normal levels | Teach/test/twist progression, secrets, NPC continuity, performance budgets |
| D — World 2 Boss & Integration | Luminous Sentinel and complete World 2 lifecycle | Boss, map/progression/save migration if required, E2E and package check |
| E — World 3 Prototype | Prove Ember Polarity and Hollow visual grammar | State interactions readable with old mechanics and accessibility modes |
| F — World 3 Full Production | Four larger levels and midpoint encounter | Drowned Archive encounter, secret history, balanced routes |
| G — World 3 Boss & Revelation | Hollow Regent and central historical reveal | Narrative coherence for normal/secret players; migration and E2E |
| H — World 4 Systems & Nonlinear Map | Prove branch graph and mastery combinations | Cinder Gate + three-order prototype, save/map semantics verified |
| I — World 4 Full Production | Entry, three branches, Last Conduit | All mechanics recur; final pacing and optional Veil material authored |
| J — Final Boss & Ending | First Keeper, Network, Ember stages | Canonical ending, credits flow, whole-campaign persistence |
| K — Whole-Game Balance | Difficulty/economy/pacing pass | Full-game playtest telemetry by observation only; no online analytics |
| L — Production Asset Replacement | Replace approved placeholders | Original/licensed art/audio inventory and performance checks |
| M — Full-Game QA | External-tester-ready complete game | Clean/returning/secret/failure/controller/display/platform matrix |
| N — 1.0 Release Preparation | Native release candidates | Packaging, signing decisions, licenses, clean machines, release notes |

## Approximate content envelope (PROPOSED)

- World 2: five normal levels plus boss; roughly 12–16 secrets; 3–4 new enemy roles; 2–3 meaningful NPC appearances.
- World 3: four larger levels, one midpoint encounter, one boss; roughly 10–14 secrets; 3 new roles plus adapted old enemies; 2–3 NPC appearances.
- World 4: entry level, three nonlinear branches, Last Conduit, final sanctum/encounter; roughly 12–16 secrets; primarily mastered combinations with at most 2 new roles; cast convergence used sparingly.

Exact collectible counts and stage lengths wait for graybox pacing. Existing power-ups and collectibles remain the baseline. Any save schema change belongs to the milestone that first persists new state and must preserve all World 1 data.

## Engineering prerequisites before Milestone C (approved 2026-11-08)

Scope is the full four-world game. Before World 2 content is registered, the following engineering work lands first:

1. **Repository health (done):** GitHub Actions verification on Linux/Windows, `v0.1.0-alpha` tag, current README, and decomposition of `core/game.py` plus the densely compressed one-line modules into readable code with no behavior change.
2. **Multi-world foundation (done):** a world list instead of the single `DEFAULT_WORLD_REGISTRY`; save schema 4 with lossless v3 migration (all World 1 results, secrets, Ember Veil reveal, boss defeat, dialogue flags, playtime); a boss registry replacing hardcoded `ashen_warden` checks in `BossSystem`, `Game`, `world_complete`, and the World Map panel; data-driven world-complete text; per-world background/theme selection; an all-prerequisites map unlock predicate for World 4; and world-to-world travel on the map.
3. **Human playtest gate:** World 1 and the Ember Currents prototype checklist in `HUMAN_PLAYTEST.md`, completed by a person, before Milestone C tuning is treated as canon.
