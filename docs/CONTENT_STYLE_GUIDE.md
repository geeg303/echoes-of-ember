# Content Style Guide

## Naming

- World names evoke place plus idea: `Verdant Reaches`, proposed `Glassreach Expanse`, `Hollow Deep`, `Crown of Cinders`.
- Level display names are 2–5 evocative words, tied to a landmark/action; IDs use stable lowercase world/number keys and never derive progression from filenames.
- Enemy names describe silhouette/behavior rather than real brands or existing franchise designs.
- Major guardian titles use role/material/idea (`Ashen Warden`, `Luminous Sentinel`, `Hollow Regent`, `First Keeper`) without escalating into arbitrary superlatives.

## Dialogue and narrative

Use concise, speakable platformer lines. Each node should reveal character, actionable observation, or evidence—preferably two, never pure lore dump. Characters interpret imperfectly. Avoid modern technical jargon, faux-archaic overload, repetitive farewell text, and declaring secrets before discovery. Environment poses questions; dialogue supplies perspectives, not encyclopedic answers.

## Level and visual identity

Every stage has a readable foreground, landmark rhythm, recovery space, and dominant motif. Teach → test → twist each major idea. Introduce one unknown at a time, combine it later, then provide calm before goals/bosses. Decorative assets cannot resemble hazards or collision. World palettes must retain value/silhouette contrast and non-color cues.

## Difficulty and checkpoints

World roles: Learn → Combine → Adapt → Master. Difficulty rises through decisions and combinations, not surprise, enemy health, or crowded noise. Checkpoints follow meaningful multi-minute accomplishments and precede major synthesis/bosses; do not trivialize each obstacle. Respawn must never depend on an expired power, dead enemy, or inaccessible platform state.

## Collectibles and secrets

Ember Shards breadcrumb rhythm, arcs, jumps, alternate routes, and risk. Rare Crystals reward mastery. Secret Tokens mark deep history. Avoid random scatter. Optional paths reconnect and use fair repeated clue language. Never add a currency simply to populate HUD/economy.

## Enemies and bosses

Each enemy owns a gameplay role and readable silhouette, anticipation, active threat, response, and defeat. Reuse an existing archetype unless the new behavior changes player decisions. Boss attacks always telegraph, threaten, recover, and expose vulnerability consistently; phase changes are unmistakable and mechanically safe. World mechanics appear in the world boss.

## Tutorials and accessibility

Teach primarily through safe layout, collectible lines, enemy isolation, and concise NPC observations. Avoid repeated modal tutorials. Critical information must survive Effects Off, mute, vibration off, and color differences through geometry, icons/text, pattern, timing, or animation. Maintain 1280×720 safe-area/readability standards and dynamic input prompts.

## Production quality gate

Before registering content: validate schema/references/bounds/safe spawn/goal; editor round-trip; debug inspection; clean and failure scenarios; checkpoint/replay/save behavior; culling/performance; keyboard/simulated controller; packaged resource manifest. Human review remains required for pacing, fairness, audio, physical controllers, and display comfort.
