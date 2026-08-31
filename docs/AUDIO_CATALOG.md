# Audio Catalog

All IDs are defined in `data/audio/audio.json`. Generated files are original temporary WAV placeholders.

## Sound and ambience IDs

| ID | Bus | Priority | Instances | Cooldown | Path |
|---|---|---:|---:|---:|---|
| `player_jump` | sfx | 1 | 2 | 0.060s | `sounds/player/jump.wav` |
| `player_land` | sfx | 1 | 2 | 0.100s | `sounds/player/land.wav` |
| `player_damage` | sfx | 2 | 2 | 0.150s | `sounds/player/damage.wav` |
| `player_death` | sfx | 3 | 1 | 0.500s | `sounds/player/death.wav` |
| `powerup_ember` | sfx | 2 | 2 | 0.150s | `sounds/powerups/ember.wav` |
| `powerup_wind` | sfx | 2 | 2 | 0.150s | `sounds/powerups/wind.wav` |
| `powerup_aether` | sfx | 2 | 2 | 0.120s | `sounds/powerups/aether.wav` |
| `powerup_stone` | sfx | 2 | 2 | 0.150s | `sounds/powerups/stone.wav` |
| `stone_guard_break` | sfx | 2 | 2 | 0.150s | `sounds/powerups/stone_break.wav` |
| `ember_pulse_fire` | sfx | 1 | 4 | 0.080s | `sounds/combat/pulse_fire.wav` |
| `ember_pulse_hit` | sfx | 1 | 4 | 0.060s | `sounds/combat/pulse_hit.wav` |
| `enemy_hit` | sfx | 1 | 4 | 0.060s | `sounds/combat/enemy_hit.wav` |
| `enemy_defeat` | sfx | 2 | 3 | 0.120s | `sounds/combat/enemy_defeat.wav` |
| `armored_block` | sfx | 2 | 2 | 0.150s | `sounds/combat/armored_block.wav` |
| `turret_fire` | sfx | 1 | 3 | 0.120s | `sounds/combat/turret_fire.wav` |
| `ember_shard` | sfx | 1 | 4 | 0.025s | `sounds/collectibles/ember_shard.wav` |
| `rare_crystal` | sfx | 2 | 2 | 0.120s | `sounds/collectibles/rare_crystal.wav` |
| `secret_token` | sfx | 2 | 2 | 0.200s | `sounds/collectibles/secret_token.wav` |
| `checkpoint_activate` | sfx | 2 | 2 | 0.200s | `sounds/world/checkpoint.wav` |
| `breakable_destroy` | sfx | 1 | 3 | 0.080s | `sounds/world/breakable.wav` |
| `switch_activate` | sfx | 1 | 2 | 0.120s | `sounds/world/switch.wav` |
| `door_open` | sfx | 1 | 2 | 0.200s | `sounds/world/door.wav` |
| `platform_warning` | sfx | 0 | 2 | 0.250s | `sounds/world/platform_warning.wav` |
| `platform_drop` | sfx | 1 | 2 | 0.200s | `sounds/world/platform_drop.wav` |
| `secret_discovered` | sfx | 2 | 2 | 0.300s | `sounds/secrets/discovered.wav` |
| `challenge_complete` | sfx | 2 | 2 | 0.300s | `sounds/secrets/challenge.wav` |
| `secret_exit` | sfx | 3 | 1 | 0.500s | `sounds/secrets/exit.wav` |
| `ui_move` | ui | 1 | 2 | 0.050s | `sounds/ui/move.wav` |
| `ui_confirm` | ui | 2 | 2 | 0.080s | `sounds/ui/confirm.wav` |
| `ui_cancel` | ui | 1 | 2 | 0.080s | `sounds/ui/cancel.wav` |
| `ui_locked` | ui | 2 | 2 | 0.150s | `sounds/ui/locked.wav` |
| `ui_notification` | ui | 1 | 2 | 0.120s | `sounds/ui/notification.wav` |
| `route_unlock` | ui | 2 | 2 | 0.200s | `sounds/ui/route_unlock.wav` |
| `ember_veil_reveal` | ui | 3 | 1 | 0.400s | `sounds/ui/veil.wav` |
| `sanctum_unlock` | ui | 3 | 1 | 0.400s | `sounds/ui/sanctum.wav` |
| `world_complete` | ui | 3 | 1 | 0.700s | `sounds/ui/world_complete.wav` |
| `level_complete` | ui | 3 | 1 | 0.500s | `sounds/ui/level_complete.wav` |
| `warden_awaken` | sfx | 3 | 1 | 0.500s | `sounds/boss/awaken.wav` |
| `warden_ground_slam` | sfx | 3 | 2 | 0.250s | `sounds/boss/ground_slam.wav` |
| `warden_bolt` | sfx | 2 | 3 | 0.100s | `sounds/boss/bolt.wav` |
| `warden_ember_rain` | sfx | 3 | 1 | 0.400s | `sounds/boss/ember_rain.wav` |
| `warden_leap` | sfx | 2 | 2 | 0.200s | `sounds/boss/leap.wav` |
| `warden_charge` | sfx | 2 | 2 | 0.250s | `sounds/boss/charge.wav` |
| `warden_core_burst` | sfx | 3 | 2 | 0.250s | `sounds/boss/core_burst.wav` |
| `warden_phase_transition` | sfx | 3 | 1 | 0.700s | `sounds/boss/phase.wav` |
| `warden_hurt` | sfx | 2 | 3 | 0.080s | `sounds/boss/hurt.wav` |
| `warden_defeat` | sfx | 3 | 1 | 1.000s | `sounds/boss/defeat.wav` |
| `ambience_verdant` | ambience | 0 | 1 | 0.000s | `ambience/verdant.wav` |
| `ambience_canopy` | ambience | 0 | 1 | 0.000s | `ambience/canopy.wav` |
| `ambience_ravine` | ambience | 0 | 1 | 0.000s | `ambience/ravine.wav` |
| `ambience_ruins` | ambience | 0 | 1 | 0.000s | `ambience/ruins.wav` |
| `ambience_sanctum` | ambience | 0 | 1 | 0.000s | `ambience/sanctum.wav` |

## Music IDs

| ID | Loop | Fade in | Fade out | Path |
|---|---|---:|---:|---|
| `music_world_map` | True | 1.00s | 1.00s | `music/world_map.wav` |
| `music_verdant` | True | 0.80s | 0.80s | `music/verdant.wav` |
| `music_ravine` | True | 0.80s | 0.80s | `music/ravine.wav` |
| `music_ruins` | True | 0.80s | 0.80s | `music/ruins.wav` |
| `music_boss` | True | 0.50s | 1.20s | `music/boss.wav` |
| `music_world_complete` | True | 0.80s | 1.20s | `music/world_complete.wav` |
