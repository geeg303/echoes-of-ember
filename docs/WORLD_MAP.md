# World Map architecture and authoring

The World Map is an authored graph in `data/worlds/verdant_reaches.json`. It contains immutable nodes, connections, waypoints, and unlock requirements. `WorldMapRuntime` owns only navigation state; `WorldProgress` owns progression.

## Nodes

```json
{
  "id": "node_verdant_02",
  "type": "level",
  "level_id": "verdant_02",
  "title": "1-2  Whispering Canopy",
  "x": 455,
  "y": 255
}
```

Supported types are `start`, `level`, `world_goal`, `optional`, and `secret`. Level nodes must reference a registered level ID. Secret placeholders never load nonexistent level content.

## Connections and waypoints

```json
{
  "id": "route_01_02",
  "from": "node_verdant_01",
  "to": "node_verdant_02",
  "waypoints": [[350, 400], [385, 310]],
  "unlock": {"type": "level_complete", "level_id": "verdant_01"}
}
```

Waypoints make routes wind through the map. Supported requirements are `always`, `level_complete`, `secret_exit_discovered`, and `world_complete`. Secret-exit requirements also include `exit_id`.

Node states are hidden, locked, available, completed, and mastered. Connection states are hidden, locked, available, and traversed. Mastered currently means the latest result has a Gold rating.

## Performance versus progression

`LevelResult` is the immutable performance snapshot from one completed run. `WorldProgress.results` stores the latest snapshot and may change after replay.

Monotonic runtime progression is stored separately:

- levels completed once;
- secret exits discovered;
- map nodes revealed;
- world completed once.

These flags never regress during the current process. A lower-scoring replay may replace displayed performance without relocking routes. Phase 13 will serialize both categories.

## Controls and flow

- Arrows/WASD: choose an available connected route.
- Enter/Space: enter a level or activate a landmark.
- M: abandon gameplay or return from results to the map.
- R on results: replay the completed level.
- Escape on the map: quit safely.

Normal startup opens the map. `python main.py --level verdant_03` bypasses it for development. Abandoning a run creates no result and changes no progression flags.

To author another map: create stable node IDs, place nodes inside 1280×720, add registered level references, connect them with unique connection IDs, add optional waypoints and unlock requirements, provide one valid start and world-goal node, then run `python -m tools.validation --all-levels`.

## Persistence

The map graph remains authored data. Phase 13 saves only the latest results, monotonic progression flags, and the last node reached after travel settles; node states and connections are derived again on load. Secret branch visibility and world completion therefore survive later lower-scoring or normal-exit replays. See [SAVE_SYSTEM.md](SAVE_SYSTEM.md).
