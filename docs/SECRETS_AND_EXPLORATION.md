# Secrets and exploration

Secrets are optional same-level regions stored in the root `secrets` array. They never alter the mandatory Ember Gate requirement.

## Types and triggers

- `secret_cache`: compact reward space; 250 discovery score.
- `secret_room`: larger optional space; 500 discovery score.
- `challenge_room`: `defeat_all` or `reach_target`; 750 completion score.
- `alternate_route`: optional traversal branch; 500 discovery score.
- `secret_exit`: alternate interactable goal; 1,000 score and a distinct result marker.

Supported triggers are `enter_region`, `interact`, `defeat_all`, and `reach_target`. A `defeat_all` challenge lists stable enemy IDs; unrelated enemies never affect it.

```json
{
  "id": "ravine_challenge",
  "secret_type": "challenge_room",
  "properties": {
    "trigger_type": "defeat_all",
    "bounds": [4100, 760, 700, 390],
    "enemy_ids": ["jumper_6", "turret_8"],
    "clue": "A ruined challenge sigil"
  }
}
```

Secret exits use `interact`, world-space bounds, and the normal `E` action. They record `ExitType.SECRET` and their stable ID in `LevelResult`; campaign order remains unchanged.

## State and results

Runtime state progresses through `UNDISCOVERED`, `DISCOVERED`, `ENTERED`, and `COMPLETED`. Discovery and completion rewards have one-time guards. `LevelResult` freezes discovered/total counts, completed room count, exit type, and exit ID. `WorldProgress` aggregates the latest result per level, so replay cannot double-count secrets.

Damage, life loss, checkpoint respawn, collected rewards, and defeated challenge enemies preserve current secret state. F7 and Replay reconstruct authored state. An unfinished challenge retains existing runtime enemy progress; a full restart restores it completely.

## Secret Tokens and clue language

Every Verdant Reaches level retains exactly one optional Secret Token.

- Cracked Ember stone suggests a breakable cache.
- Rising shard trails suggest optional climbs.
- Glowing vines or crystals suggest concealed passages.
- Ruin symbols suggest switches or challenges.
- A visible reward establishes a traversal objective.

Clues should be readable without explicit labels. Timed powers may make entry easier, but secrets and mandatory routes require safe, recoverable exits.
