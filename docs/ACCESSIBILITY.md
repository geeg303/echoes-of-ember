# Accessibility

Echoes of Ember is fully playable with keyboard or a Pygame-supported controller. Prompts change with the most recently used device. Menus support keyboard arrows/Enter/Escape and controller D-pad or stick/face buttons; gameplay actions do not depend on mouse input.

## Readability and non-color cues

Selected menu rows use a border and diamond marker as well as color. World Map nodes use distinct lock, check, star, secret, boss, goal, and current-position glyphs. The Ashen Warden HUD displays `CORE OPEN` with a diamond when damage is possible. Stone Guard shows a named HUD status and charge. Text is placed on high-contrast panels inside a 40×32 safe area at the 1280×720 internal resolution.

## Motion and effects

The existing Effects Quality option also controls camera shake:

- Full: authored particles, flashes, and full shake intensity.
- Reduced: fewer optional effects and 50% shake intensity.
- Off: optional effects and camera shake are suppressed; persistent sprites, geometry, warnings, text, and telegraphs remain.

This uses application-settings schema 2; no migration is required. Screen flashes are short and opacity-capped. Vibration has an independent on/off setting and is never required for play.

## Audio independence

Master mute and separate Music, SFX, Ambience, and UI levels are available. Damage, goals, map state, dialogue, boss vulnerability, and platform warnings all retain visual communication with audio unavailable or muted.

## Known limitations

Key/button rebinding, subtitles for purely atmospheric sounds, font-size choices, high-contrast palettes, and dedicated photosensitivity presets are not yet implemented. Physical Xbox-, PlayStation-, and Nintendo-style controller feel and subjective audio balance require human review on representative hardware.
