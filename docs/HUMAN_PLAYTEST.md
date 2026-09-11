# Human Playtest Handoff

## Automated verified

The verification suite covers clean and returning campaign journeys, map/level/boss progression, representative secret discovery, normal and boss failure/retry, save and achievement persistence, keyboard and simulated-controller input, dynamic prompts, audio fallback, effects quality, validators, performance scenarios, and the 18,000-frame soak. Deterministic developer captures cover Main Menu, Settings, Achievements, World Map, HUD gameplay, Pause, Dialogue, Level Complete, boss play, and Game Over.

## Human review recommended

No claim is made that Codex physically held a controller, listened through speakers/headphones, or judged a real monitor's fullscreen presentation. Before release packaging, a human should:

1. Play the clean-profile World 1 route through Ashen Warden on keyboard.
2. Repeat representative play with Xbox-, PlayStation-, and Nintendo-style/generic SDL controllers.
3. Judge movement, moving-platform feel, turret warning time, boss learnability, and camera comfort.
4. Listen to music/SFX/ambience at defaults, muted, and at extreme mixer settings on speakers and headphones.
5. Toggle Full, Reduced, and Off effects; confirm warnings remain clear and Off is comfortable.
6. Exercise windowed/fullscreen switching, focus loss/restore, and non-native desktop scaling.
7. Review every save-slot state and destructive confirmation wording.
8. Read Mira, Orin, Talen, and Vesper dialogue in normal play and inspect all secrets without debug assistance.
9. Use the editor with a mouse for pan, zoom, paint, erase, undo/redo, validate, save, and playtest.

For the Glassreach prototype, directly launch `prototype_glassreach_currents` and record answers for counter-push feel, immediate direction/strength recognition, Pulse bending clarity, lift control, Wind Boots/Aether Wing identity, moving-platform fairness, flyer readability, and whether the combined room feels meaningfully distinct from World 1. No automated run is a substitute for these responses.

Record hardware, OS, display scale, controller model, audio device, observed issue, reproduction steps, and severity for each finding.
