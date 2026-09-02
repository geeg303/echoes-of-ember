# Persistent Save System

Phase 13 persists committed campaign progress; it never suspends a running level. `core.save_manager.SaveManager` is the only filesystem boundary, while `systems.save_data.SaveSession` owns schema conversion and rebuilds `WorldProgress` from validated JSON. `CURRENT_SAVE_VERSION` in `systems/save_data.py` is the sole schema-version constant.

## Location and slots

Production saves use a per-user application-data directory:

- Linux: `$XDG_DATA_HOME/echoes_of_ember/saves`, or `~/.local/share/echoes_of_ember/saves`
- Windows: `%LOCALAPPDATA%/echoes_of_ember/saves`
- macOS: `~/Library/Application Support/echoes_of_ember/saves`

Tests inject a temporary `save_root`; they never touch production saves. Three fixed slots are supported. A slot uses `slot_N.json`, `slot_N.json.bak`, and transient `slot_N.json.tmp` files, where `N` is 1, 2, or 3. Slot IDs are validated before paths are constructed. Deletion removes only the chosen slot's primary, backup, and stale temporary files.

Normal campaign startup uses slot 1. Choose another with `python main.py --slot 2`. `python main.py --slot 2 --new-game` explicitly replaces that slot with a fresh campaign. New campaigns start at Starting Grove with no results or monotonic flags. `--new-game` is intentionally explicit; the programmatic API refuses an occupied slot unless overwrite is requested.

`python main.py --level verdant_03` remains a nonpersistent development launch. It cannot read or modify campaign slots. It cannot be combined with `--new-game`.

## Version 3 schema

A sanitized abbreviated save looks like this:

```json
{
  "schema_version": 3,
  "metadata": {
    "slot_id": 1,
    "created_at": "2026-08-31T12:00:00Z",
    "updated_at": "2026-08-31T12:18:30Z",
    "play_time_seconds": 1110.25
  },
  "campaign": {
    "active_world_id": "verdant_reaches",
    "current_map_node": "node_verdant_03",
    "level_results": {
      "verdant_01": {
        "completed": true,
        "completion_time": 281.4,
        "score": 8200,
        "ember_shards_collected": 43,
        "ember_shards_total": 52,
        "rare_crystals_collected": 2,
        "rare_crystals_total": 3,
        "secret_tokens_collected": 1,
        "secret_tokens_total": 1,
        "enemies_defeated": 8,
        "enemies_total": 12,
        "deaths": 1,
        "lives_remaining": 2,
        "health_remaining": 3,
        "checkpoints_activated": 2,
        "rating": "SILVER",
        "secrets_discovered": 1,
        "secrets_total": 3,
        "secret_rooms_completed": 1,
        "exit_type": "normal_exit",
        "exit_id": "ember_gate"
      }
    },
    "progression": {
      "completed_levels_once": ["verdant_01", "verdant_02"],
      "discovered_secret_exits": [],
      "revealed_map_nodes": [],
      "defeated_bosses": [],
      "dialogue_flags": ["met_mira"],
      "completed_worlds_once": []
    }
  }
}
```

Authored level files and the world registry remain authoritative for graph topology, coordinates, content totals, and secret definitions. Saves store the latest completed `LevelResult` for each level plus separate monotonic discoveries. A later replay replaces the latest result but cannot revoke completed-once, secret-exit, revealed-node, or world-completed-once flags. Best-result ranking is intentionally deferred.

The meaningful current map node is persisted only after map travel reaches a node. Fractional connection travel is derived runtime state and is not saved.

## Deliberately excluded runtime state

The schema does not contain player position or velocity, partial collectible state, checkpoints from unfinished runs, enemies or their health, projectiles, power-up timers or Stone Guard, platform/tile timers, current combat or animation state, camera offsets, or secret-room temporary state. Quitting mid-level therefore resumes safely on the World Map using the last committed campaign snapshot.

## Autosave and play time

Autosaves occur after a completed level has produced its `LevelResult` and all monotonic progression flags, after returning to the map, and after map travel settles on a destination node. Clean shutdown performs a final safe save. UI/render changes do not mark the session dirty. Play time accumulates once per game update across map, gameplay, and result screens, then continues from the saved cumulative value after loading; repeated saves do not add prior time again.

## Atomic writes, backup, and recovery

Saving serializes the complete payload, writes and flushes a same-directory temporary file, calls `fsync`, then installs it with `os.replace`. Before replacement, a validated primary is copied through a temporary backup and atomically installed as the one last-known-good `.bak`. Invalid primary data is never promoted into the backup.

Loading validates the primary first and then the backup. A valid backup yields `RECOVERED` and a visible map warning. If neither validates, the slot is reported as `CORRUPT`; the files remain untouched and persistence is disabled for that session until an explicit new-game reset. A newer schema is `UNSUPPORTED_VERSION` and is also left untouched. Empty, valid, recovered, corrupt, and unsupported states are available through slot inspection for the future slot menu. Stale temporary files are ignored and removed during inspection.

## Validation and migration

Validation covers root structure, schema and slot IDs, UTC-compatible timestamps, finite nonnegative play time and result numbers, authored world/level/node/secret IDs, enum values, duplicate progression entries, and impossible completion totals. JSON is used directly; pickle and recursive runtime serialization are forbidden.

`migrate_save()` is the single version-dispatch entry. Version 1 loads directly. Future versions are rejected safely, and older versions require an explicit known migration path before loading. No fake migration is included.

## Programmatic API

`SaveManager` provides `list_slots`, `inspect_slot`, `new_game`, `load`, `save`, and `delete`. `SlotSummary` exposes completion, score, secrets, tokens, play time, last update, and recovery state without exposing filesystem details. Save failures are logged and leave the active in-memory campaign playable.

## Version 1 → 2 migration

Schema 2 adds the monotonic `defeated_bosses` list and makes authored boss defeat the source of truth for world completion. The real v1→v2 migration preserves timestamps, play time, map node, level results, completed levels, secret exits, revealed nodes, tokens, and Ember Veil. It initializes `defeated_bosses` to empty.

Phase 13 considered Verdant Reaches complete after all four platforming levels, before a boss existed. Migration deliberately clears that legacy `completed_worlds_once` flag rather than falsely claiming the Ashen Warden was defeated. Ruins remains completed, so First Flame Sanctum is available immediately; the player must defeat the boss once to establish true World 1 completion. The migration chain then adds dialogue flags and the next successful save writes the snapshot atomically as schema 3.

## Phase 17 front-end integration

Normal startup inspects three slots through summaries. Continue chooses the newest valid or recovered slot; corrupt slots can be explicitly reset/deleted and unsupported versions are protected. Pause/Game Over exits never serialize unfinished runtime state or create a failed result. Application preferences live in separate schema-1 `settings.json`; campaign schema remains 2.

## Version 2 → 3 migration

Version 3 adds validated `progression.dialogue_flags`. Loading a v2 slot inserts an empty list and preserves results, completed levels, secret exits, revealed nodes, defeated bosses, world completion, timestamps, current node, and play time. Pure conversation-history flags save immediately when first granted rather than waiting for level completion. Invalid, duplicate, or malformed flags reject the slot safely.

## Achievement profile isolation

Local achievements use a separate schema-1 `achievements.json` beside this save directory. Slot creation, overwrite, deletion, recovery, and campaign schema migration never read, reset, or embed achievement state. Campaign schema remains 3.

## Editor isolation

Editor playtests construct nonpersistent temporary runtime state. They never load or write campaign slots, and editor files are not automatically registered into campaign progression.
# Debug isolation

`--debug --slot N` loads a slot for read-only inspection but suppresses autosave and achievement-profile writes. `--debug --new-game` is rejected to prevent accidental overwrite. Debug commands, completion attempts, dialogue flags, and secret reveals remain memory-only.

## Phase 24 verification

Isolated tests cover empty/valid/corrupt/future slots, backup recovery, slot independence, invalid fields, atomic replacement failure, schema 1→2→3 migration, reload after every World 1 stage, secret-route monotonicity, boss-gated world completion, and debug/direct/editor persistence isolation. Verification tools redirect user data to a temporary root.
