# Debug Command Reference

Open the developer palette with backtick. Commands are predefined, validated, transient, and available only after launching with `--debug`. `GAMEPLAY` commands are rejected outside a loaded level; `GLOBAL` commands are safe in front-end, map, and gameplay contexts.

| Command | Context | Purpose | Persistence |
|---|---|---|---|
| `help [command]` | Global | List commands or show syntax/help | Read-only |
| `status` | Global | Show debug pause, time scale, and taint | Read-only |
| `god [on\|off]` | Gameplay | Toggle damage immunity | Taints; transient |
| `heal` | Gameplay | Restore health through Player API | Taints; transient |
| `damage [1..99]` | Gameplay | Exercise normal enemy-damage/guard path | Taints; transient |
| `lives <0..99>` | Gameplay | Set a validated lives value | Taints; transient |
| `powerup <type>` | Gameplay | Activate ember_pulse, wind_boots, aether_wing, or stone_guard | Taints; transient |
| `clear_powerup` | Gameplay | Clear the primary power-up through PowerUpSystem | Taints; transient |
| `teleport <x> <y>` | Gameplay | Teleport within authored pixel bounds | Taints; transient |
| `teleport checkpoint\|goal\|boss` | Gameplay | Teleport to a known runtime landmark | Taints; transient |
| `checkpoint list` | Gameplay | List checkpoint IDs | Read-only |
| `checkpoint <id>` | Gameplay | Activate checkpoint semantics | Taints; transient |
| `spawn_enemy <type> [x y]` | Gameplay | Spawn through the configured enemy factory | Taints; transient |
| `clear_enemies` | Gameplay | Remove enemies without score/achievement events | Taints; transient |
| `boss status` | Gameplay | Show boss state | Read-only |
| `boss damage <1..99>` | Gameplay | Controlled damage preserving phase/defeat invariants | Taints; transient |
| `boss reset` | Gameplay | Reset boss, arena, hostile shots, and encounter ability | Taints; transient |
| `secret list` | Gameplay | List secret states | Read-only |
| `secret reveal <id>` | Gameplay | Reveal a known secret without progression writes | Taints; transient |
| `save status` | Global | Show slot/schema/completion and write-disabled state | Read-only |
| `achievement status` | Global | Show schema, enabled state, counts, and dirty state | Read-only |
| `dialogue status\|close` | Global | Inspect or safely close dialogue | Close is transient |
| `audio status\|mute` | Global | Inspect audio or toggle session mute | Mute is transient |
| `effects status` | Global | Inspect quality and particle cap | Read-only |
| `effects full\|reduced\|off` | Global | Override quality for this session | Taints; transient |
| `effects stress` | Global | Emit a bounded known stress burst | Taints; transient |
| `pause` | Global | Toggle debug simulation pause | Transient |
| `step` | Gameplay | Advance one update and remain paused | Transient |
| `timescale <0.25\|0.5\|1\|2>` | Gameplay | Set bounded simulation scale | Transient |
| `repro` | Global | Export safe diagnostic JSON | Diagnostic file only |
| `perf export` | Global | Export bounded rolling metrics | Diagnostic file only |
| `screenshot` | Global | Save the current internal frame | Diagnostic file only |

Examples:

```text
help teleport
powerup ember_pulse
teleport checkpoint
boss damage 4
timescale 0.25
repro
```

Unknown commands, malformed quoting, wrong argument counts, invalid enums, out-of-range numbers, and invalid contexts return a visible error. No command accepts source code or arbitrary filesystem paths.
