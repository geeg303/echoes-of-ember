# Echoes of Ember level authoring

Levels are validated JSON files loaded independently of their filenames. To create one, duplicate `data/levels/verdant_01.json`, immediately replace its stable `id`, and keep the raw definition separate from runtime state.

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
python -m tools.validation --all-levels
python main.py --level your_level_id
```

Register the level ID in explicit campaign order in `data/worlds/verdant_reaches.json`. The command-line selector accepts registered IDs only; it never accepts arbitrary paths. Continue uses this registry rather than filename sorting.

## Design template

Use teach → test → twist for each mechanic. Put optional challenges above or beside a safe main route, reconnect branches, place checkpoints after learning milestones, and end with a calm gate reveal. Verify that power-up expiration, destroyed blocks, opened doors, and defeated enemies cannot softlock the mandatory path.


## Registering a level on the World Map

Add one `level` node with the stable registered `level_id`, map coordinates, and title. Connect it using unique connection IDs, optional route waypoints, and an authored unlock requirement. Do not infer order from filenames. Validate the complete registry with `python -m tools.validation --all-levels`; see `docs/WORLD_MAP.md` for the graph schema.

## Save compatibility

Level IDs, secret-exit IDs, and map-node references are persistent identifiers once shipped. Renaming one can invalidate an existing save unless a future schema migration maps the old identifier. Never add live entity state to the save schema: only a frozen completed `LevelResult` and monotonic campaign discoveries cross the persistence boundary.
