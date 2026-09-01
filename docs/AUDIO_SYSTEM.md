# Audio and Music System

## Authority boundary

`AudioManager` is a presentation service. Authoritative gameplay outcomes issue audio requests; playback success, channel availability, sound completion, music position, and mixer state never control movement, attacks, bosses, results, progression, or saves. Effects and audio independently observe the same event.

## Architecture

`core/audio_manager.py` owns mixer initialization, device-failure fallback, catalog parsing, lazy sound caching, music state, ambience owners, runtime settings, mute, channel selection, cooldowns, instance limits, positional panning, request history, reset, and shutdown. `data/audio/audio.json` contains sound and music definitions. Gameplay refers only to stable IDs.

`AudioSettings` provides runtime-only master, music, SFX, ambience, UI, and future voice volumes. Effective volume is `master × bus × definition`. Every value is clamped to 0–1. Muting applies zero effective volume without deleting selected music or ambience context. Persistence is deferred to the settings-menu phase; campaign save schema remains 2.

## Buses and defaults

| Bus | Default |
|---|---:|
| Master | 1.00 |
| Music | 0.75 |
| SFX | 0.85 |
| Ambience | 0.60 |
| UI | 0.80 |
| Voice (future) | 0.85 |

Priorities are Ambient, Normal, Important, and Critical. Important/critical requests may force a channel when all 24 channels are occupied. Definitions also specify cooldown and maximum simultaneous instances. Missing/unknown assets are cached failures and log once, then become safe no-ops.

## Music and ambience

The manager tracks one current and one pending music ID. Re-requesting the same track does not restart it. Context changes use definition-driven fade-out/fade-in durations. Map, Verdant, ravine, ruins, boss, and world-complete tracks are available. The Ashen Warden track starts on encounter activation, does not restart across phases, and fades after defeat. Music never drives boss timing.

Ambience uses explicit owners (`map` or `level`). Starting the same owner/loop twice is idempotent; replacing it stops the old channel. F7, replay, life loss, boss reset, map/level transitions, and shutdown clear and reconstruct the correct context without duplicate loops.

## Positional audio

World SFX may provide a world position and Nova/listener X. The manager applies lightweight stereo panning and modest distance attenuation with a 35% minimum. Critical visual telegraphs remain authoritative, and critical audio does not use aggressive inaudibility.

## No-audio and headless behavior

If mixer initialization fails, audio is explicitly disabled and all APIs remain safe. Use `SDL_AUDIODRIVER=dummy` in CI. A forced nonexistent driver was verified: map/game startup and clean shutdown still work. Dependency injection also permits `AudioManager(enabled=False)` for complete audio-off gameplay tests.

## Placeholder assets

`tools/generate_placeholder_audio.py` deterministically creates 22.05 kHz mono WAVs from original sine layers and seeded noise. Short cues use amplitude envelopes; ambience and music use gentle loop envelopes. Assets are temporary, modest-amplitude, compact, and contain no downloaded or imitated melodies. Run with `--force` to regenerate all 58 files.

## Adding audio

1. Add a unique ID to `data/audio/audio.json`.
2. Choose path, bus, base volume, priority, instance cap, and cooldown. Music also defines loop and fades.
3. Add or generate the file under the organized `assets/sounds`, `assets/music`, or `assets/ambience` path.
4. Request the ID only after the authoritative event succeeds.
5. Test disabled/missing-asset behavior and rapid repetition.
6. Never wait for playback to advance gameplay.

## Debug and future settings UI

With `DEBUG_MODE`, F8 toggles master mute while preserving context. Clean volume/mute setters are ready for Phase 17 controls. Runtime audio request history and peak/active channel counters support tests and profiling but are not serialized.

## Validation and performance

The suite covers mixer success/failure, disabled mode, catalogs, unknown and missing assets, bus validation, volume clamp, mute, cooldowns, instance limits, priority metadata, positional playback, music transitions, ambience ownership, reset, player/world/map/boss event requests, no-audio gameplay, and save isolation.

600-frame audio-only results: normal 0.0098 ms mean, rapid shards 0.0296 ms, combat 0.0183 ms, and boss Phase 3 requests 0.0192 ms. Integrated boss gameplay measured 9.896 ms mean, 11.320 ms p95, 31.337 ms max, and three peak channels. The Phase 15 mean was 9.018 ms; audio added about 0.878 ms while p95 remained below the 16.67 ms frame budget.

## Phase 17 menu and settings integration

Front-end, slot, settings, Pause, and Game Over controls request stable UI cues. Master/Music/SFX/Ambience/UI sliders and mute apply immediately through `AudioManager` and persist in application settings, not campaign saves. Menus and all transitions remain functional with no audio device or with mute enabled.
# Debug diagnostics

The Audio page and `audio status` expose availability, mute state, music/ambience ownership, channel count, and recent event data without starting loops. `audio mute` is a transient session override.
