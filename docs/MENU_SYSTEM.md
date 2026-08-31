# Menu and Front-End System

## Player flow

Normal `python main.py` startup opens the procedural title front-end. Continue, New Game, Load Game / Save Slots, Settings, Credits, and Quit are presented through `FrontendController`; direct `--level` and explicit `--slot` launches remain available for development. Continue selects the most recently updated valid or recovered slot.

## Reusable controls

`ui/menu.py` owns logical menu actions, focus movement, disabled-item skipping, sliders, selectors, confirmation dialogs, and common drawing. Arrows or WASD navigate; Enter/Space confirm; Escape backs out. Confirmation dialogs focus Cancel by default. Focus uses a diamond marker, border, and color, so selection is not color-only. The architecture is keyboard-first and ready for Phase 18 device mapping.

## Save slots

The front-end presents exactly three slots from `SaveManager` summaries and never parses saves during drawing. Empty slots can start a new campaign. Occupied slots require overwrite confirmation. Valid or recovered slots can play or be deleted; deletion is confirmed. Corrupt slots may be reset or deleted, while unsupported future-version slots are protected and disabled. Recovery is labeled visibly.

## Lifecycle and performance

Fonts and controllers are created once. Save summaries refresh only when entering or mutating the slot flow. Title particles use the bounded `EffectsSystem`; audio uses stable `ui_move`, `ui_confirm`, and `ui_cancel` requests and remains safe when muted or unavailable. Front-end effects/audio are cleared and reconfigured on gameplay, map, and main-menu transitions.

## Controller integration

Menus now consume logical actions from `InputManager`. D-pad and stick navigation use bounded repeat; south face confirms, east face cancels, and Start resumes Pause. Focus and dialogs are unchanged, destructive dialogs still default to Cancel, and active-device prompt text updates without reloading a screen. Held transition inputs are suppressed until release.
