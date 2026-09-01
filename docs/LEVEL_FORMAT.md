# Authoritative Level Format

Level JSON is validated by `tools.validation` and loaded by `world.level.Level`. Required root fields include stable ID/name/world/number/display metadata; description/theme/time and rating targets; declared collectible totals; completion requirements; width, height, and tile size; one `player_spawn`; `goal`; sparse `tiles`; `objects`; and `secrets`. `boss_encounter` is optional. Forward-compatible valid extension fields are preserved by the editor.

Tiles are sparse rectangles: `{"id": 1, "position": [0, 16], "size": [12, 2]}`. IDs 0–7 mean empty, solid, one-way, hazard, decorative, breakable, bounce, and slippery. An edited tile layer may be serialized as equivalent 1×1 records.

Objects use stable IDs and world-space x/y. Collectibles are `ember_shard`, `rare_crystal`, `secret_token`, and `health_item`. Enemies use type `enemy`, an `enemy_type` of crawler/flyer/jumper/turret/armored, and validated properties. Power-ups use type `powerup` and `powerup_type`. World objects cover checkpoint, moving platform (horizontal/vertical), falling platform, disappearing platform, switch, and door. Switch target IDs must resolve to doors.

Secrets are separate records with ID, `secret_type` (`secret_cache`, `secret_room`, `challenge_room`, `alternate_route`, `secret_exit`), and properties containing trigger type, rectangular bounds, clue/reward, and enemy references where required. The goal is an `ember_gate` with position and `requires_interact`.

NPC placements remain companion files at `data/npcs/<level_id>.json`; the editor preserves/atomically writes placement IDs, display/style/facing/radius, position, and references to existing dialogue IDs. Dialogue graphs are not level data.

Boss stages optionally contain `boss_encounter`: boss ID/spawn, arena bounds, trigger bounds, locking door IDs, and pulse source. These fields are loaded, visualizable, validated, and preserved without exposing boss AI graphs.
