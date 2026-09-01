# World 1 NPCs

World 1 uses four recurring-tone guides, one in each platform stage and none in the boss arena.

- **Mira — Verdant Beginning:** welcomes Nova, teaches Ember Shard trail-reading, offers an introductory choice, remembers the first meeting, reacts to discovered secrets, and reacts to the Ashen Warden defeat.
- **Orin — Whispering Canopy:** teaches readable moving/falling platforms, remembers the first meeting, rewards secret awareness, and reacts to the Warden defeat.
- **Talen — Emberfall Ravine:** warns about the Sanctum, switches, sentries, and breakable glowing stone; later reframes the Warden victory.
- **Vesper — Ruins of the First Flame:** hints at the Ember Veil without exposing its route, explicitly recognizes discovery of `v04_secret_exit`, and reacts to completed World 1.

First-meeting variants use `flag_missing`; their end nodes set `met_mira`, `met_orin`, `heard_sanctum_warning`, or `vesper_secret_hint`. Lower-priority repeat variants use the corresponding `flag`. Secret, secret-exit, boss, and world-complete variants have higher priority, so replaying a level reveals the most relevant authored reaction. Vesper’s Veil acknowledgement sets `vesper_veil_acknowledged` once but remains a safe repeatable conversation.

The cast provides hints and lore only. NPCs do not grant quests, inventory, powers, scores, unlocks, or combat authority.

## Story achievements

Completed conversations contribute unique profile-wide NPC identities. Repeating one speaker cannot inflate `Four Voices`; meeting the four guides across different campaign slots may contribute.
