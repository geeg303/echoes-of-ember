# Echoes of Ember — Game & Content Bible

Status labels: **CANON** is implemented or approved high-level truth; **PROPOSED** guides production but may be revised; **OPEN QUESTION** needs creative approval; **DEFERRED** is outside the current roadmap.

## Identity

**CANON.** Echoes of Ember is an original colorful fantasy 2D action-platformer about exploration, responsive traversal, readable combat, hidden routes, and the cost of controlling change. The player fantasy is to become Nova: an agile explorer who reads a living world, follows scattered Ember, uncovers suppressed history, and ultimately changes the system rather than merely repairing it.

Current release identity is `0.1.0-alpha — World 1 Vertical Slice`. It is not the complete game.

## Pillars

1. **Movement is trust.** Controls, camera, hazards, and platforms remain responsive and legible.
2. **Curiosity changes understanding.** Optional routes provide mechanical rewards and earlier narrative truth.
3. **Old tools gain new meanings.** Later worlds combine established movement, power-ups, enemies, and interactables before adding mechanics.
4. **Bosses embody ideas.** Each Warden tests its world's mechanics and advances the argument about safety and control.
5. **Challenge is fair and recoverable.** Telegraphs precede threats; checkpoints respect pacing; required paths never depend on expiring optional power.

## Tone and themes

Wonder sits beside melancholy, never nihilism. Humor and warmth may come from character observation, not parody. Ruins are evidence of lives and choices, not generic decay. The central tension is **control versus freedom/change**. Freedom can be dangerous; control can begin as care. The story rejects both effortless utopia and cartoon villainy.

## Nova

**CANON:** Nova is an explorer who follows Ember Shards through Verdant Reaches, helps no faction through a quest/inventory system, and defeats the Ashen Warden. **CANON full-game arc:** Discovery → Doubt → Revelation → Choice. Nova begins by believing something valuable was lost and can be restored. She learns the accepted catastrophe story is incomplete, discovers decline was tied to deliberate containment, and chooses decentralized renewal over restoring central authority.

**PROPOSED:** Nova communicates through action and concise responses rather than long speeches. Her defining trait is willingness to revise a hopeful belief when evidence changes.

## Ember

**CANON full-game truth:** Ember is a natural force of creation, memory, transformation, and renewal. It did not simply vanish: civilizations harnessed it, then divided and contained its flow. Its unpredictability brings real risk, but suppressing change slowly impoverishes the world. Ember Shards remain common guidance/score collectibles; Rare Crystals signify mastery; Secret Tokens mark deep exploration and hidden history.

## Wardens and history

**CANON full-game truth:** Sanctums and Wardens were created to regulate dangerous Ember. Their mandate drifted from protecting people, to protecting Ember from people, to preserving centralized control. The network materially contributed to the remembered collapse and ongoing decline. Individual Wardens need not be corrupted; obedience to a flawed mandate is central to the tragedy.

## Four-world dramatic structure

| World | Dramatic movement | Mechanical movement | Outcome |
|---|---|---|---|
| Verdant Reaches | Discovery | Learn | Nova sees fading beauty, hidden history, and defeats the Ashen Warden. |
| Glassreach Expanse | Doubt | Combine | Evidence contradicts the accepted catastrophe account; the Sentinel works as designed. |
| Hollow Deep | Revelation | Adapt | Buried records reveal deliberate centralization and systemic responsibility. |
| Crown of Cinders | Choice | Master | Nova confronts the First Keeper and redirects the network. |

World names 2–4 remain **PROPOSED working names** pending creative approval.

## Ending direction

**CANON direction:** one canonical ending. Nova dismantles central control without releasing all stored Ember at once. She redirects/decentralizes the network; regional relationships resume gradually, Wardens lose central authority, and risk remains. The promise is not “everything is fixed,” but **the world can change again**. Player action may enact this outcome; no artificial good/evil menu is required.

## Rules for future content

- A new mechanic must recur, combine with old tools, appear in its world boss, and support secrets.
- Each world receives one dominant mechanical identity; one-off gimmicks remain rare.
- Existing power-ups stay relevant; at most one or two additional powers may be proposed with demonstrated level value.
- No new currency without a unique long-term purpose. Secret Tokens are not ordinary shop money.
- New enemies fill distinct spatial/decision roles, not stronger recolors.
- Mandatory routes survive power expiration, missed collectibles, enemy defeat, and changed interactable state.
- Secrets are fairly hinted and narratively valuable; completionists learn truth earlier, not a different truth.
- Exposition is divided among environment, play, NPC perspectives, bosses, and secrets.
- Boss mechanics reuse world vocabulary and retain anticipation → threat → recovery.
- Accessibility is authoritative: important state never relies only on color, audio, vibration, or optional effects.
- Every content milestone extends validators, scenarios, editor support, debug inspection, performance coverage, and packaging manifests.

## World 1 canonical audit

**CANON shipped data:** Verdant Reaches contains Verdant Beginning (52 shards/3 rare/1 token/2 secrets), Whispering Canopy (56/3/1/3), Emberfall Ravine (62/3/1/3), Ruins of the First Flame (68/4/1/4), then First Flame Sanctum. The map branches from Ruins to the hidden Ember Veil and gates the Verdant Beacon behind `ashen_warden` defeat. Mira, Orin, Talen, and Vesper appear once each in levels 1–4. The Sanctum supplies a checkpoint, health, and encounter-safe Ember Pulse.

The Ashen Warden has 18 health and three implemented phases: Ground Slam/Ember Bolt/Heavy Advance; Ground Slam/Double Bolt/Ember Rain/Leap Slam; then Fast Slam/Rain/Charge-Leap/Core Burst. It teaches telegraph, dodge, and punish; it is not stomp-vulnerable.

**Documented tension, not retcon:** `verdant_restored` and World Complete express the characters' World 1 understanding, not proof the systemic crisis is solved. Talen's “protect without becoming a cage” line reflects a partial hopeful interpretation before later evidence. “Verdant Reach” in the 1-1 subtitle is a local/singular wording variant; the registered world is **Verdant Reaches**.

## Open questions and recommended defaults

- **World names:** keep the three working names through prototypes; approve before full production.
- **First Keeper origin:** recommended ancient distributed stewardship intelligence consolidated into a singular authority; avoid a surprise human mastermind.
- **Does Nova speak?** recommended sparse selectable/short responses, no fully silent or exposition-heavy protagonist.
- **Additional ability:** recommended none until World 2 prototype proves a recurring design gap.
- **World 4 branches:** recommended free branch order after Cinder Gate, all three required for Last Conduit.
- **Secret Token gate:** recommended optional Veil lore thresholds, never mandatory campaign progress.

## Deferred

Exact collectible counts, final art/audio, final dialogue scripts, new achievement definitions, platform/store integration, alternate endings, shops, inventory, skill trees, multiplayer, and Worlds 2–4 production data are deferred.
