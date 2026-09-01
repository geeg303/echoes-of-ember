# Achievement System

Achievements are profile-wide presentation metadata. Authoritative gameplay emits semantic outcomes; `AchievementManager` observes them, updates profile progress, evaluates validated definitions, persists unlocks, and queues presentation. Gameplay, progression, damage, map unlocks, and saves never read achievement state.

## Profile schema

`achievements.json` lives beside the `saves` directory and uses schema 1. It stores only unlock UTC timestamps, bounded known counters, known set-style progress, and semantic flags. Definitions remain in `data/achievements/achievements.json`. The three campaign slots remain schema 3 and settings remain schema 2.

Writes use a same-directory temporary file, flush, fsync, and atomic replace. Unlocks save immediately; ordinary counter/set changes are dirty-tracked and flushed at completion, transitions, or clean shutdown. Corrupt and unsupported-future profiles are logged once, preserved, and replaced in memory by a safe disabled empty profile so startup and campaign files remain unaffected.

## Definitions and evaluation

Definitions contain stable ID, title, description, category, visibility, condition, sort order, and procedural style. Categories are progression, exploration, combat, secrets, collectibles, story, and challenge. Visibility is visible or hidden. Conditions support `event`, `flag`, `counter_at_least`, `set_contains_all`, `all_of`, and `any_of`; arbitrary code is forbidden.

Events update only relevant counters/sets and then evaluate the small catalog once. No evaluation occurs per frame or render. Unlocks are idempotent: a repeated event never changes the original timestamp or creates another toast. Lifetime Shard/enemy actions count across legitimate replays; NPC, secret, level, and boss progress use unique IDs across all slots.

## Runtime policy

Normal campaign/front-end launches enable achievements. `--level` explicitly disables profile loading, evaluation, and writing. New Game, slot overwrite/delete, Game Over, F7, and replay never reset the global profile. Attempt-only `damage_taken_this_attempt` resets with the level and is not serialized. A fully absorbed Stone Guard hit is not health damage.

The Main Menu Achievement screen supports category filtering, scrolling, hidden spoilers, clamped counter progress, keyboard, and controller. Unlock toasts are bounded, serial, input-independent, and about 3.6 seconds. Pause and dialogue freeze their timer; dialogue hides the toast until closed; boss completion defers it until the result presentation. Audio/effects are optional.

## Adding an achievement

Add a unique definition with a unique sort order, choose an existing semantic event/counter/set, avoid gameplay rewards, validate the catalog, and add focused tests. Add a new semantic hook only at an authoritative outcome boundary—not inside rendering or achievement UI.

## Editor isolation

Editor and F5 playtests explicitly disable achievement profile loading, events, counters, unlocks, and writes.
# Debug isolation

Achievement observation and profile writes are disabled for every `--debug` session. Achievement-worthy debug actions may appear in the bounded semantic trace but cannot unlock or modify the real profile.
