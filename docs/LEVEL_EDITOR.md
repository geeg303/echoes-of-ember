# Built-In Level Editor

Launch the developer-only editor with `python main.py --editor --level verdant_01`. Use `--smoke-test` for five headless frames. It is intentionally absent from the player Main Menu and imported lazily, so normal startup pays no editor initialization cost.

## Architecture and safety

`LevelDocument` owns a deep-copied authoritative JSON payload, optional NPC companion catalog, source path, selection, validation results, and dirty state. Unknown fields remain untouched. The editor writes the same JSON consumed by `Level.load`; there is no editor format or converter. `CommandHistory` stores bounded deep snapshots (150 actions), while `EditorViewport` is the single screen/world/tile transform.

Save validates first, writes a temporary file, flushes/fsyncs, atomically replaces, reloads through the authoritative validator, and restores a backup if installation/revalidation fails. Invalid data cannot overwrite a valid level. Save As is available through `LevelDocument.save(path, level_id)` and never registers the new file in campaign data. Shrinking refuses objects that would fall outside bounds. Closing a dirty UI defaults to Cancel and presents Save/Discard/Cancel.

## UI and tools

The 1280×720 layout uses palette/tools left, culled viewport center, JSON-informed inspector right, and counts/status/diagnostics below. Procedural symbols require no external art.

- Left click: paint/place/select
- Right click: erase tile
- Middle drag: pan
- Wheel: bounded 25%, 50%, 75%, 100%, 150%, 200% zoom
- Tab: paint/object/select
- R: rectangle tool (two corners, one command)
- `[` / `]`: tile type
- Comma / period: object palette
- Arrow keys: move selected object by 8 px
- Ctrl+C / Ctrl+V / Ctrl+D: copy/paste/duplicate with fresh IDs
- Delete: remove selected object
- Ctrl+Z / Ctrl+Y or Ctrl+Shift+Z: undo/redo
- G: grid
- 1–5: layer visibility
- V: authoritative validation
- Ctrl+S: validated atomic save
- F5: isolated normal-runtime playtest and return

The palette covers spawn, Ember Gate, all collectibles, five enemies, four power-ups, checkpoints, horizontal/vertical/falling/disappearing platforms, switches, doors, breakable tile ID 5, five secret types, and NPC placement. Complex boss metadata is preserved losslessly and arena/trigger data remains authoritative; Phase 21 deliberately does not offer a boss-AI editor.

## Playtest isolation

F5 serializes the current in-memory payload to a temporary directory, validates it, creates a temporary registry entry, and launches the normal `Game`/`Level` runtime. Persistence and achievements are disabled. The temporary `WorldProgress`, dialogue flags, results, Game Over state, and projectiles disappear on return. Campaign slots, application settings, achievement profile, production level, and dirty document are untouched.

## Worlds 2–4 workflow

Create a `LevelDocument.new`, choose safe dimensions, paint readable terrain, position spawn and goal, add objects with unique IDs, validate, Save As under `data/levels`, playtest, and only then intentionally add the ID to a world registry. Dialogue, achievements, world-map topology, audio, sprites, and boss AI remain authored by their dedicated data/code systems.

## Known limitations

The inspector presents safe structured data and keyboard movement but is not a full form/table editor for every advanced field. New NPC dialogue content, map registration, boss behavior, background authoring, and advanced recovery snapshots remain outside Phase 21. A hands-on mouse/zoom/inspector usability review is recommended before large-scale Worlds 2–4 production.
