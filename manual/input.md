# Input

Game code never checks keys. It reads **actions**: `ctx.actions.axis2("move")`, `ctx.actions.pressed("jump")`.
Which keys, mouse buttons and gamepad inputs drive an action is data, so players can rebind keys and gamepads work without changing game code.

## Bindings

Actions live in `assets/input.bindings`, an engine table edited in the Tables panel (or through CSV). Each row is one action, and the row id is the action name:

```text
row move
kind Axis2
label Move
keys W S A D Up Down Left Right
pad LeftStick

row jump
label Jump
keys Space
pad A
```

| Columns | Meaning |
|---|---|
| `kind` | `Button` (pressed or not), `Axis` (-1 to 1), `Axis2` (2D, length at most 1), `Delta` and `Delta2` (amount this frame, for turning a camera or zooming) |
| `label` | The name players see in the settings screen |
| `keys` | Key names: letters, digits, `Space`, `Enter`, `Shift`, `Up`, `F1` ... An `Axis` takes keys in pairs (negative, positive), an `Axis2` in groups of four (up, down, left, right). `-` leaves a place empty |
| `mouse` | Buttons `Left`, `Right`, `Middle`, `WheelUp`, `WheelDown`; amounts `Wheel`, `Move`, `MoveX`, `MoveY` (pixels and wheel notches as they are) |
| `pad` | Gamepad buttons `A`, `B`, `X`, `Y`, `LeftShoulder`, `Start`, `DPadUp` ...; sticks and triggers `LeftStick`, `RightStick`, `DPad`, `LeftX`, `LeftTrigger` ... |
| `rate` | For `Delta` actions: the amount per second from keys and sticks |
| `deadzone` | Stick and trigger dead zone (0 to 1) |

Several bindings add up: a button is down when any of its inputs is, and an `Axis2` is cut to length 1, so diagonal keys move at the same speed as straight ones.
The file is reloaded when it changes, so edits in the Tables panel apply at once during play.

## Reading actions

| Call | Value |
|---|---|
| `down("jump")`, `pressed("jump")`, `released("jump")` | Held, pressed this frame, released this frame |
| `axis("zoom")` | `Axis` and `Delta` values |
| `axis2("move")` | `Axis2` and `Delta2` values (y is up) |
| `lastDevice()` | Keyboard and mouse, or gamepad: the device used last, for button prompts |

While the game does not have the keyboard or mouse (the editor's game view is not focused, or the window is in the background), every action reads as released.
An action name that is not in the table reads as zero and logs one warning.

Action values are only seen by the view side. The game turns them into its 8-byte input (`GameInput`) for each tick, so input bindings never affect the simulation or the content hash.

## Gamepads

On Windows the engine reads Xbox and XInput-compatible gamepads (four slots) and passes the first connected one to the actions. Unconnected slots are checked once a second, because checking an empty slot is slow.
A `-` in front of a gamepad input makes it the negative side, so two buttons make one axis: `pad DPadUp -DPadDown`. A trigger bound to a `Button` action is pressed from halfway.
Gamepads are only read while the game window has focus (in the editor, while the game view has the keyboard). PlayStation and Switch controllers are not supported yet.

## Player bindings

Keys a player changes are saved in the user folder (`%LOCALAPPDATA%\<game>\input.bindings` on Windows), holding only the rows that differ from the project. They are applied on top of the project file, so a game update that adds actions keeps the player's other keys.
The Keys tab of the settings screen changes them (see {doc}`settings`).
