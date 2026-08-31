# Echoes of Ember level authoring

Levels are validated JSON files loaded independently of their filenames. To create one, duplicate `data/levels/level_01.json`, immediately replace its stable `id`, and keep the raw definition separate from runtime state.

## Required metadata

Define `id`, `name`, `world_id`, positive `level_number`, `display_name`, `description`, `theme`, positive `time_target`, declared collectible totals, `completion_requirements`, `rating_thresholds`, and one `goal`. Progression must never infer identity from the filename.

Choose `width`, `height`, and `tile_size` in grid cells, then place `player_spawn` in pixel coordinates inside a safe empty region. Give the map explicit side boundaries and a safe floor or bounded hazards.

## Content workflow

1. Add tile placements to `tiles` using an ID, grid `position`, and optional rectangular `size`.
2. Add collectibles to `objects` and update the declared totals to match.
3. Add enemies with stable IDs, `enemy_type`, pixel coordinates, and validated properties.
4. Add power-ups using `type: "powerup"` and `powerup_type`.
5. Add moving platforms with axis, distance, and speed; falling and disappearing platforms use timing properties.
6. Create switches and doors with unique IDs, then reference doors through `target_id` or `target_ids`.
7. Place checkpoints at safe player top-left respawn coordinates.
8. Define one top-level Ember Gate goal. Keep the mandatory route completable without a timed power-up.

```json
"goal": {
  "type": "ember_gate",
  "x": 6690,
  "y": 896,
  "properties": {"requires_interact": true}
}
```

Validate and run:

```bash
python -m tools.validation data/levels/your_level.json
python main.py
```

The current build loads `level_01.json`. A future selector should pass another path through the same `Level.load` and runtime reconstruction flow without changing gameplay code.

## Design template

Use teach → test → twist for each mechanic. Put optional challenges above or beside a safe main route, reconnect branches, place checkpoints after learning milestones, and end with a calm gate reveal. Verify that power-up expiration, destroyed blocks, opened doors, and defeated enemies cannot softlock the mandatory path.
