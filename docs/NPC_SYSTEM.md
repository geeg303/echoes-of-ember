# NPC System

## Definition and placement

NPCs are non-solid, non-damaging world entities loaded from `data/npcs/<level_id>.json`. Each catalog is a list containing a stable `id`, `display_name`, matching `level_id`, `[x, y]` world position, finite positive interaction radius, procedural `style`, initial `facing`, and one or more dialogue variants. Positions are validated against level bounds. NPC IDs must be unique within the catalog.

```json
{
  "id": "mira_v01",
  "display_name": "Mira",
  "level_id": "verdant_01",
  "position": [310, 896],
  "interaction_radius": 82,
  "style": "mira",
  "facing": "right",
  "dialogues": [
    {"dialogue_id": "mira_intro", "priority": 20,
     "conditions": [{"type": "flag_missing", "value": "met_mira"}]}
  ]
}
```

`NPCSystem` owns catalog loading, nearest-in-range selection, condition evaluation, variant priority, and active speaker state. A fallback variant should always be authored. The highest-priority matching variant wins deterministically.

## Interaction and lifecycle

The screen prompt appears only above the nearest in-range NPC and uses the active input device label. `E` or controller north-face/Y starts conversation through the logical `INTERACT` action. Critical authored interactions resolve first: switches/checkpoints, secrets, and the level goal; NPC interaction follows. One edge cannot activate multiple systems.

NPCs bob subtly while idle. While talking they face Nova. They do not collide with Nova, enemies, tiles, or projectiles and never modify gameplay state directly. F7/replay rebuilds NPC runtime state and closes dialogue. Level/map/menu transitions clear the active speaker. Persistent dialogue flags remain because they belong to campaign progress, not the level runtime.

## Adding an NPC

Create or reuse validated dialogue files, add a catalog entry for the desired level, keep the NPC on safe ground within bounds, give every variant a known dialogue ID, and run the narrative validation/tests. No change to `Game`, `Player`, or collision code is required.

## Editor placement

The level editor places/repositions references in the per-level NPC companion catalog. It does not author dialogue graphs. F5 dialogue state is temporary and never enters a campaign slot.
# Debug diagnostics

Trigger visualization shows NPC IDs and interaction radii. The inspector exposes copied primitive identity/bounds data, and the dialogue diagnostic reports the active conversation without revealing or mutating persistent story state.
