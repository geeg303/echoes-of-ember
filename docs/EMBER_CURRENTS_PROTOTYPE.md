# Ember Currents Prototype

## Runtime semantics

An Ember Current is an authored rectangular world-space region. Its immutable definition contains an ID, bounds, normalized direction, strength in pixels-per-second squared, explicit affected categories, initial enabled state, and visual style. `EmberCurrentSystem` owns transient enabled/reversed state, overlap queries, additive influence, rendering, and reset. It never moves another object directly.

Current influence is acceleration composed with existing velocity before authoritative collision resolution. Nova retains input, jumping, coyote/buffer behavior, moving-platform carry, damage knockback, and power-up modifiers. Player projectiles curve through acceleration while keeping faction, lifetime, collision, and count limits. Existing flyers may opt in with `current_affected`; all other enemies remain unchanged. Moving platforms retain authored motion; the rider receives platform displacement and Current acceleration independently. Platform-body displacement by Currents is deferred.

Overlapping vectors add and the result is clamped to 1,800 px/s². Runtime direction is normalized. Definitions support horizontal, vertical, and arbitrary vectors. F7/new level reconstruction restores authored enabled state and direction. Nothing is saved.

## Level format

`ember_currents` is an optional root list; omission means no Currents and preserves World 1 behavior.

```json
{"id":"current_lift_01","bounds":[1024,320,512,640],"direction":[0,-1],"strength":900,"affects":["player","player_projectiles"],"enabled":true,"style":"lift"}
```

Allowed targets are `player`, `player_projectiles`, and `flyers`. Styles are `glassreach`, `lift`, and `strong`. Strength must be finite, greater than zero, and no more than 5,000. Bounds must be positive and inside the level. IDs share uniqueness with ordinary objects. Direction must be finite and nonzero. Unknown fields and categories are rejected.

## Authoring and debugging

In the editor, choose `ember_current`, place its default rectangle, select by clicking inside, move with arrows, and use standard delete, duplicate, copy/paste, undo/redo, save, validation, and F5/Shift+F5 playtest. Bounds and direction arrows remain visible. The structured inspector exposes all authored fields; prototype numeric tuning beyond the default remains a JSON task.

With `--debug`, F4 shows Current bounds, ID, direction, strength, targets, and enabled state. The World page shows total/active/overlapping Currents and player influence. Clicking a region produces a primitive read-only inspector. Commands are `current list`, `current status ID`, `current enable ID`, `current disable ID`, and `current reverse ID`; mutations are transient.

## Presentation and production constraints

Thin boundaries and repeated high-contrast arrow glyphs communicate region, direction, and approximate strength independently of particles, color, or sound. The geometry remains under Full, Reduced, and Off effects. Current audio is deferred.

- Show a Current before mandatory entry and provide recovery after strong pushes.
- Avoid blind pushes into hazards.
- Keep projectile routes visible and short enough to read.
- Limit overlapping regions to combinations whose resultant direction is apparent.
- Use Currents to combine known mechanics, not merely impede movement.
- Prefer fewer than eight active/visible Currents in production rooms; 16 is stress-only.

Spline flows, Current-driven platform bodies, switch-linked metadata, production ambience, and final Glassreach art are deferred pending human playtest.
