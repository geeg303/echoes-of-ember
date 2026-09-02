# Dialogue System

## Data schema

Each file in `data/dialogue` defines one graph with a globally unique `id`, a valid `start` node ID, and a non-empty `nodes` list. Supported node types are `line`, `choice`, `system`, and `end`. Line/system nodes may use `next`; choice nodes contain non-empty `responses` with `label`, `target`, optional `conditions`, and optional safe `effects`. End nodes close after their text is revealed and confirmed.

```json
{
  "id": "mira_intro",
  "start": "start",
  "nodes": [
    {"id": "start", "type": "line", "speaker": "Mira",
     "text": "Follow the scattered light.", "next": "answer"},
    {"id": "answer", "type": "choice", "speaker": "Mira", "text": "Ready?",
     "responses": [{"label": "I am.", "target": "end"}]},
    {"id": "end", "type": "end", "speaker": "Mira", "text": "Then go.",
     "effects": [{"type": "set_flag", "value": "met_mira"}]}
  ]
}
```

Validation rejects malformed JSON, duplicate/empty IDs, unknown node types, missing targets, empty choice nodes, bad condition/effect types, oversized text, invalid flag names, and unreachable nodes. Dialogue data cannot execute Python or directly mutate gameplay.

## Conditions and safe effects

Whitelisted conditions are `flag`, `flag_missing`, `level_completed`, `boss_defeated`, `secret_exit_found`, `secret_found`, `secret_token`, and `world_completed`. Values are strongly typed. The only effect is `set_flag`, whose value must match the semantic lower-snake-case flag format. Flags are idempotent.

Conversation-history flags commit immediately to the selected campaign slot and survive death, F7, replay, level failure, and later sessions. They are intentionally independent of `LevelResult`. Schema 3 adds `progression.dialogue_flags`; v2 slots migrate with an empty set while preserving all previous progress.

## Runtime and UI

`DialogueSystem` owns graph position, typewriter progress, filtered choices, focus, transitions, completion, and effect dispatch. `DialogueBox` owns screen-space wrapping and presentation. Confirm reveals the current line immediately on first press, then advances/selects on the next. Up/down changes a visible choice; Back closes this optional dialogue. Prompts follow the active keyboard/controller device.

While dialogue is active, player physics/input, enemies, boss, projectiles, platforms, collectibles, hazards, camera simulation, effects simulation, level timer, deaths, and save play-time accumulation are frozen. Audio continues. Pause is suppressed; Back closes dialogue. The existing world remains rendered under a translucent dialogue layer.

## Adding dialogue

Create one graph file, keep every target reachable, use only whitelisted conditions/effects, reference it from an NPC variant, provide an unconditional fallback, and run `pytest` plus the narrative data validation. Text is wrapped at render time; fonts are cached by the game rather than recreated per frame.

## Achievement observation

A meaningfully completed conversation emits one semantic NPC completion event after dialogue closes. Toast presentation is deferred while dialogue is visible. Dialogue never checks achievement state.

## Editor playtest

Existing NPC dialogue can run in isolated editor playtests; semantic flags exist only in temporary WorldProgress and disappear on return.
# Debug diagnostics

The read-only Progression page and `dialogue status` report active dialogue state. `dialogue close` uses the normal close/end APIs. Debug sessions never persist dialogue flags.

Phase 24 traverses all 15 authored graphs, verifies every node is reachable and can reach a terminal, validates NPC references, and covers condition priority, effects, persistence, keyboard/controller flow, and complete simulation freeze while dialogue is open.
