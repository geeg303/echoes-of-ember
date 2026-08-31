# The Ashen Warden

The Ashen Warden is an original ancient stone-and-Ember guardian beneath First Flame Sanctum. Mossed stone limbs, carved armor, fiery cracks, and an exposed Ember core connect the encounter to Verdant Reaches and the Ruins of the First Flame. All current art is drawn procedurally with Pygame primitives.

## Arena and entry

`verdant_boss` is a focused 36×14-tile level. Its short safe entry supplies a checkpoint, health, and a normal Ember Pulse pickup before the authored arena trigger. During the encounter, an Ember source grants ranged attack permission for the entire fight, preventing expiration or zero-power-up softlocks. Doors at both arena edges close on entry and reopen after defeat. Enter or Space skips the three-second awakening intro.

## Core tuning

- Maximum health: 18
- Phase 1: 18–13 health
- Phase 2: 12–7 health
- Phase 3: 6–1 health
- Ember Pulse damage: existing value of 1
- Contact/projectile damage: 1
- Boss hit invulnerability: 0.18 seconds
- Defeat sequence: 3 seconds
- Defeat score: 5,000, exactly once

Stomping does not damage the Warden. The bright outlined core communicates an active Ember Pulse vulnerability window.

## Phase 1 — Awakened Guardian

- Ground Slam: 0.7-second glow/raise, two ground shockwaves, approximately 1-second vulnerable recovery.
- Ember Bolt: 0.55-second core flash, one aimed projectile, short armored recovery.
- Heavy Advance: 0.45-second warning, slow readable pressure, 0.7-second recovery.

This phase teaches telegraph → dodge → punish.

## Phase 2 — Fractured Warden

A 1.4-second invulnerable transition intensifies cracks without damaging Nova. The attack pool retains Ground Slam and adds:

- Double Ember Bolt: two controlled angles rather than bullet-hell density.
- Ember Rain: 0.85-second warning lines/circles with one safe lane, then four falling fragments and a 1.1-second vulnerable recovery.
- Leap Slam: a marked landing location, shockwaves, and a 1.15-second vulnerable recovery.

## Phase 3 — First Flame Unbound

The final transition exposes a brighter core and selects from faster learned patterns:

- Fast Ground Slam: shorter but visible anticipation.
- Ember Rain: established safe-lane language.
- Charge/Leap: faster position pressure followed by recovery.
- Core Burst: strong 0.8-second telegraph, eight radial projectiles with readable gaps, and a longer 1.4-second final punish window.

Attack selection cycles deterministically through the current phase pool and excludes the immediately previous attack. This prevents repetition and keeps tests reproducible.

## Reset, result, and progression

A life loss returns Nova to the Sanctum checkpoint and reconstructs Phase 1 at full health with projectiles and temporary encounter state cleared. F7 performs the same full authored reset. A committed lethal boss hit wins simultaneous-death resolution and stabilizes Nova for the defeat sequence.

Defeat creates the `verdant_boss` result with exit ID `ashen_warden`, adds the monotonic `ashen_warden` boss flag, completes Verdant Reaches, opens the post-boss Verdant Beacon summary node, and autosaves. Replays may replace the latest boss result but cannot revoke those flags.

## Human tuning review still required

Automation verifies state safety, not fun. Physical playtesting should review total 2–4 minute duration, core visibility, Ground Slam jump timing, rain warning readability, Phase 2/3 pressure, projectile speed, camera framing, HUD readability, arena width, Stone Guard usefulness, and whether an 18-health encounter feels satisfying rather than repetitive.

## Audio presentation

Original placeholder cues cover awakening, ground slam, bolts, Ember Rain, leap, charge, core burst, phase transitions, hurt, and defeat. The dedicated boss loop begins during awakening and is independent of phase/state timing. A muted or unavailable mixer leaves every telegraph and encounter rule unchanged.

## Pause and Game Over

Pause freezes every Warden state, timer, projectile, arena hazard, and effect update while audio context may continue. A final-life loss never counts as a Warden defeat. Game Over releases the arena and Retry recreates the Ashen Warden at 18 health, Phase 1, with no stale projectiles or vulnerability state.
