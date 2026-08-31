# Input System

## Dependency direction

All physical input flows through `core/input_manager.py`:

```text
keyboard / Pygame joystick / simulated backend
                    ↓
              InputManager
                    ↓
              logical Action
                    ↓
        game host / menu controllers
```

Gameplay entities, physics, menus, bosses, and world objects never query joystick hardware. `PlayerControls` continues to receive movement intent and jump state, preserving the established movement engine.

## Logical actions

Gameplay actions are `MOVE_LEFT`, `MOVE_RIGHT`, `MOVE_X`, `JUMP`, `ATTACK`, `INTERACT`, and `PAUSE`. Menu actions are `MENU_UP`, `MENU_DOWN`, `MENU_LEFT`, `MENU_RIGHT`, `CONFIRM`, and `BACK`. Debug effects/reset/mute/attack actions remain keyboard-only. Physical controls may map to different logical actions by context: the south face button produces Jump and Confirm, and only the active state consumes the relevant action.

## Keyboard and controller mapping

Keyboard behavior is preserved: A/D or arrows move, Space/Z/Up jumps, F attacks, E interacts, Escape pauses/backs out, Enter/Space confirms, and WASD/arrows navigate menus. Gamepad defaults are left stick or D-pad for movement/navigation, south face for Jump/Confirm, west face for Attack, north face for Interact, east face for Back, and Start/Menu for Pause. Names are normalized; gameplay does not branch on controller brand.

## Controller normalization

The first stick is processed through a radial 0.22 deadzone. Remaining magnitude is rescaled to 0–1, preserving direction and ensuring full deflection equals keyboard maximum rather than exceeding it. Menu cardinal actions require 0.58 magnitude. A direction fires once, waits 0.38 seconds, then repeats every 0.12 seconds. This prevents stick noise and unbounded per-frame navigation.

## Edges and transitions

The manager exposes held, pressed, released, continuous-axis, and consumable edge state. State changes suppress currently held edges until release, so Confirm cannot activate two screens, Start cannot immediately unpause, and Game Over Retry cannot become an unintended first-frame jump. Focus loss clears all held state. Disconnect clears axes/buttons immediately.

## Devices, prompts, and hot-plug

`PygameControllerBackend` discovers devices once at startup and responds to add/remove events; it does not enumerate hardware every frame. One deterministic active controller is used: the current controller remains selected while connected, otherwise the lowest available instance ID is chosen. Safe metadata includes instance ID, display name, and GUID, but none is persisted.

The most recent meaningful keyboard key or controller button/stick movement selects the active device. Analog noise inside the deadzone does not change it. `get_prompt()` resolves textual labels such as ENTER/E/F/ESC or A/Y/X/START without requiring copyrighted glyph assets.

## Testing and future rebinding

`FakeControllerBackend` supports device connection, disconnection, axes, buttons, D-pad, identity, and rumble in headless CI without hardware mocks scattered through tests. The logical action boundary is ready for future rebinding; Phase 18 deliberately does not add a rebinding UI or persist physical instance IDs.
