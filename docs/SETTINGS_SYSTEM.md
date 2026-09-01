# Application Settings System

## Ownership and schema

`SettingsManager` stores application preferences in a separate `settings.json` beside the platform save directory. It never modifies campaign slots, whose current schema is version 3. Application settings use schema version 2 (schema 1 migrates automatically):

```json
{
  "schema_version": 2,
  "audio": {"master_volume": 1.0, "music_volume": 0.75, "sfx_volume": 0.85, "ambience_volume": 0.60, "ui_volume": 0.80, "muted": false},
  "visual": {"effects_quality": "full"},
  "display": {"fullscreen": false},
  "input": {"vibration_enabled": true}
}
```

Volumes must be finite numbers and are clamped to 0–1. Toggles must be booleans; quality is `full`, `reduced`, or `off`. Missing, corrupt, malformed, or unsupported settings safely fall back to defaults. Writes use a same-directory temporary file and atomic replacement.

## Menu behavior

Settings are available from the title and Pause menus. Left/right changes volume in 5% increments with immediate `AudioManager` preview. Mute uses the manager's authoritative state. Effects quality immediately updates `EffectsSystem`; critical gameplay telegraphs remain authored outside optional particles. Fullscreen safely recreates the display while retaining the 1280×720 internal canvas. Resolution selection is intentionally deferred.

Changes save when leaving Settings and again at clean shutdown. Reset to Defaults requires confirmation, immediately reapplies defaults, and leaves campaign data untouched. Returning from Pause Settings returns to Pause rather than resuming gameplay.

## Input preferences and schema 2

Application settings schema 2 adds `input.vibration_enabled`. Schema 1 loads through an explicit additive migration with vibration enabled, and the next save writes schema 2. The Settings menu is fully controller navigable, including discrete 5% slider adjustments, selectors, fullscreen recreation, reset confirmation, and Vibration On/Off. Campaign save schema is independently versioned and currently at 3.
