# Adding a World

The engine supports any number of worlds in order (`data/campaign.json`). This is the checklist for registering Worlds 2–4. Everything here is data plus one boss registration; no other engine changes are required.

## 1. Levels

- Author levels in `data/levels/<level_id>.json` with `"world_id"` set to the new world and a known `theme` (`glassreach`, `hollow_deep`, `crown_of_cinders`; see [THEMES.md](THEMES.md)).
- Level IDs and boss IDs must be unique across the whole campaign; the campaign loader rejects duplicates.
- Validate: `python -m tools.validation --all-levels`.

## 2. Boss

- Add `data/bosses/<boss_id>.json` with a `display_name`.
- Implement the boss class (subclass `bosses.boss_base.Boss`) and register it once in `systems/boss_system.py`:

```python
register_boss_runtime("luminous_sentinel", BossRuntime(LuminousSentinel, {"awaken": "sentinel_awaken", ...}))
```

The audio map turns the boss's generic hooks (`awaken`, `phase`, `hurt`, `defeat`, ...) into sound IDs from `data/audio/audio.json`. Nothing else in the runtime names a specific boss (a guard test enforces this).

## 3. World registry and map

Create `data/worlds/<world_id>.json`:

```json
{
  "id": "glassreach_expanse",
  "display_name": "Glassreach Expanse",
  "map_theme": "glassreach",
  "levels": ["glass_01", "glass_02", "glass_03", "glass_04", "glass_05", "glass_boss"],
  "map": { "start_node": "...", "nodes": [...], "connections": [...] }
}
```

The map follows [WORLD_MAP.md](WORLD_MAP.md): one `start`, every level once, a `boss` node, a `world_goal`, and unlock rules (`all_of` for World 4's branch finale).

## 4. Gates between worlds

Add a `world_gate` node on the previous world's map, usually past its world goal, and a gate back on the new world's map:

```json
{"id": "glassreach_gate", "type": "world_gate", "target_world": "glassreach_expanse", "title": "To Glassreach", "x": 1180, "y": 200}
{"id": "beacon_to_gate", "from": "verdant_beacon", "to": "glassreach_gate", "unlock": {"type": "world_complete"}}
```

Crossing a gate also requires the campaign rule: world N opens only after world N-1's boss is defeated. Gates must target a different, existing campaign world.

## 5. Campaign

Append the world ID to `data/campaign.json`. Existing saves stay valid: worlds missing from a save start fresh, and each world remembers its own map position.

## 6. NPCs and dialogue

Per-level NPC catalogs and dialogue work unchanged. Conditions see the whole campaign, so a World 2 line can depend on World 1 (`{"type": "boss_defeated", "value": "ashen_warden"}`) or on a specific world being complete (`{"type": "world_completed", "value": "verdant_reaches"}`). Nova's own lines use `"speaker": "Nova"`.

## 7. Verify

`python -m tools.verify_project --full`, then add an end-to-end test that completes the new world and crosses its gates (see `tests/test_world_travel.py` for the pattern).
