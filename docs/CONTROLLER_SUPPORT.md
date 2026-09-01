# Controller Support

## Supported model

Echoes of Ember supports one modern controller through Pygame's normalized joystick layer. Common Xbox-style, PlayStation-style, Nintendo-style PC, and generic SDL-mapped controllers should work when Pygame exposes conventional face-button, stick, D-pad, and Start indices. Keyboard remains available at all times.

## Default layout

| Control | Gameplay | Menus / map |
|---|---|---|
| Left stick | Analog movement | Navigate |
| D-pad | Digital movement | Navigate |
| South face (A/Cross) | Jump | Confirm |
| West face (X/Square) | Ember Pulse | Replay where offered |
| North face (Y/Triangle) | Interact | — |
| East face (B/Circle) | — | Back / cancel |
| Start/Menu | Pause | Resume from Pause |

Text prompts use generic A/B/X/Y/START labels and automatically switch when meaningful keyboard or controller input is used.

## Complete controller flows

Controller input covers the title/front-end, save-slot creation/overwrite/delete dialogs, Settings sliders/selectors, Credits, World Map route selection, analog and D-pad gameplay movement, jump buffering and variable jump, Ember Pulse, switches/goals/secrets, Pause, Level Complete, Game Over, the three-phase Ashen Warden encounter, and World Complete return flow.

## Hot-plug and recovery

Controllers can connect after startup. Disconnecting immediately clears held movement and buttons; the game continues and keyboard control remains available. Reconnection requires no restart. With multiple controllers, the current active controller stays selected until removed, then the lowest available instance ID is chosen. Hardware identity is never stored in campaign or settings data.

## Vibration

Safe centralized vibration is used sparingly for player damage, Stone Guard absorption, Warden ground slams, boss phase changes, and defeat. Settings includes Vibration On/Off. Unsupported hardware and disconnects silently ignore requests. Application settings schema 2 persists only the preference and migrates schema 1 with vibration enabled by default.

## Compatibility limits

Physical controller review is still recommended across representative SDL mappings. There is no control rebinding, per-controller calibration, custom glyph pack, multiplayer ownership, Steam Input integration, or platform-specific SDK. The deadzone is centralized but not exposed in the UI.

## Dialogue

Dialogue is fully controller-operable. Prompts switch live with the active device, choice focus uses normalized menu actions, and held-button edges are suppressed across open/close transitions. Start/Pause is intentionally ignored until optional dialogue is closed with Back.
