# Input

This page explains how input actions work inside: how the bindings table is read, how keys, mouse and gamepad become action values each frame, and how a player's rebound keys are saved.
How to declare actions in a project is in {doc}`../../manual/input`. The code is in {engine}`engine/src/mealkit/input`.

`input` comes after `debug` and before `audio` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존"). It reads raw state from `platform` (`Input` for keyboard and mouse, `Gamepads` for pads) and tables through `data`.
Game code never reads keys. The view side reads action values, and the game packs them into its 8-byte `GameInput` for the simulation. Why there is one action mapping for everything is in {engine}`docs/CODING_MODEL.md` ("입력").

## The bindings table

Actions are rows of the engine table `assets/input.bindings` ({engine}`engine/src/mealkit/input/Actions.h`). The row id is the action name, and the row type is `input::Action`:

| Field | Meaning |
|---|---|
| `kind` | `Button`, `Axis` (−1..1), `Axis2` (a 2D vector up to length 1), `Delta`, `Delta2` (change this frame, for camera turning and zoom) |
| `label` | The name shown to players |
| `keys` | Key names. `Axis` takes them in pairs (negative, positive), `Axis2` in groups of four (up, down, left, right). `-` is an empty slot. |
| `mouse` | `Left`, `Right`, `Middle`, `WheelUp`, `WheelDown`, `Wheel`, `Move`, `MoveX`, `MoveY` |
| `pad` | Gamepad buttons, axes, sticks, `DPad` or triggers. A leading `-` makes the input negative. |
| `rate` | For `Delta` kinds: amount per second from keys and sticks |
| `deadzone` | Stick and trigger dead zone (0 to 1, default 0.2) |

The table is read with the same table reader as game tables (`data::loadTable`), so the editor's Tables panel edits it. It is registered as a view-only table (`kTableView`), so it is outside the content hash: every player may use different keys.

When the table is read, each row is parsed once into a `Bound` entry ({engine}`engine/src/mealkit/input/Actions.cpp`): key names become Win32 virtual key codes (letters and digits are their own codes), mouse and pad names become small enums, and a sign is kept per pad input.
Unknown names and key lists of the wrong group size are reported in the log. After this, the per-frame update never compares strings.

## One frame

The engine calls `Actions::update(input, pad, keyboardAllowed, mouseAllowed, dt)` once per frame before the game's update.
In `game::Frontend` ({engine}`engine/src/mealkit/game/Frontend.cpp`) the order is: game UI update, settings screen update, then actions. The UI goes first and may take the mouse or the keyboard, and then the actions see those devices as not pressed.

For every action:

1. **Keyboard** (only when allowed): a `Button` is down when any of its keys is down. An `Axis` adds +1 for the positive key and −1 for the negative key of each pair. An `Axis2` builds x from left and right and y from up and down.
2. **Mouse** (only when allowed): buttons and wheel directions count as buttons. `Wheel`, `MoveX` and `MoveY` add raw wheel steps or pixels. `Move` adds the mouse movement as a 2D value, scaled by the mouse sensitivity and flipped by the invert setting. Up is positive.
3. **Gamepad** (when one is connected): buttons give 1. Single axes and triggers go through a dead zone. Sticks use a round dead zone on the vector length. `DPad` becomes a 2D value. A trigger or axis used for a `Button` counts as pressed from 0.5.
4. **Combine**: `Delta` kinds multiply keys and sticks by `rate × dt`, so holding a key turns the camera at a steady speed, while mouse movement is used in pixels as it is. An `Axis` is clamped to −1..1. An `Axis2` is shortened to length 1, so moving diagonally is not faster.

`down`, `pressed` (down now, not in the previous frame), `released`, `axis` and `axis2` read the results by name.
An unknown action name returns 0 and writes one warning per name.

`lastDevice()` is `Gamepad` when a pad input was used this frame and `KeyboardMouse` when a key or the mouse was. The game can use it to show the right button prompts.

`setLookSettings` sets the mouse and pad sensitivity and the Y inversion from the player settings. The mouse values apply to every mouse `Move` input and the pad values to the stick part of `Delta2` actions (camera turning). They work on the view side, before the game packs the values for the simulation.

## Gamepads

`Gamepads` ({engine}`engine/src/mealkit/platform/Gamepad.h`) is in the platform layer. On Windows it reads XInput, with 4 slots, and the engine passes the first connected pad to the actions.
Reading an empty XInput slot is slow (about 14 µs per slot), so empty slots are checked only once per second. Why the engine uses XInput instead of a library such as SDL is in {engine}`docs/DECISIONS.md` (2026-10-18).

## Reloading

Every 0.25 seconds `update` compares the path and write time of `assets/input.bindings` and of the player's file. When one changed, both are read again.
Actions that were held stay held across the reload, so editing the table during play does not release a key in the middle of a move.

## Rebound keys

A player's own bindings are in a file in the user settings folder, normally `game::userFolder(...)` + `/input.bindings` (`setUserFile`). It has the same table format, but:

- It holds **only the rows that differ from the project**. A row is the same when `keys`, `mouse`, `pad`, `rate` and `deadzone` are all equal.
- It holds only those five fields. `kind` and `label` always come from the project, so a game update that changes an action's kind is not undone by an old user file.
- Rows for actions the project no longer has are ignored.

`setBinding` changes one action (and keeps its kind and label), `resetBinding` puts back the project value, and `saveUser` writes the file. When every row is back to the default, the file is deleted.
The standard settings screen uses these for its key rows (see {doc}`settings`).

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Action mapping | `input::Actions` | Game code reads named actions, not keys, so rebinding, gamepads and bots use the same path. |
| Data-driven bindings | `assets/input.bindings`, `data::loadTable` | Actions are table rows, edited in the editor and reloaded while the game runs. |
| Parse once, read often | `parse` into `Bound` | Names are turned into key codes and enums when the table is read, so each frame only reads numbers. |
| Rescaled dead zone | `dead1` | Values inside the dead zone are 0 and values outside are stretched back to 0..1, so there is no jump at the edge. |
| Radial dead zone | `dead2` | Applies the dead zone to the stick vector's length, which keeps diagonal directions accurate. |
| Vector length clamp | `Actions::update` for `Axis2` | Limits 2D movement to length 1, so diagonal keys are not faster than one key. |
| Frame-rate independent deltas | `rate × dt` | Keys and sticks give the same camera speed at any frame rate; mouse movement stays in pixels. |
| Edge detection | `pressed`, `released` | Compares this frame's state with the previous frame's. |
| Overlay of user changes | `Impl::load`, `saveUser` | The player file stores only differences and only the binding fields, laid over the project table. |
| Throttled device polling | `Gamepads` | Empty XInput slots are checked once per second because each check is slow. |
