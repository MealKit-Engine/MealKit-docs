# Adding a new input

**Goal**: a new button the player presses that changes the game (push, use, throw).
**From**: the sandbox sample's push (`samples/sandbox`).

Input travels in four steps: the binding table names the action, the view reads the action and packs it into the 8-byte tick input, lockstep sends those bytes to every peer, and `sim/` reads the bytes. The simulation never looks at keys or actions.

## 1. Add the action and its keys

`assets/input.bindings` is a table (edit it in the editor's [Tables] panel). One row per action, with the keys and pad buttons that trigger it:

% from: samples/sandbox/assets/input.bindings
```text
row push
label Push
mouse Left
pad RightTrigger X
```

The row's `label` is what the settings screen shows when the player rebinds it.

## 2. Give it a bit in the tick input

The tick input is the game's own 8-byte struct. Buttons are bits:

% from: samples/sandbox/sim/World.h
```cpp
inline constexpr u8 kButtonJump = 1;
inline constexpr u8 kButtonPush = 2;
```

## 3. Read the action in the view

`view/LocalInput` reads actions every frame and builds the tick input when a tick is sent. A press between two ticks is kept in a latch so a short click isn't lost:

% from: samples/sandbox/view/LocalInput.cpp
```cpp
    pushLatch |= actions.pressed("push");
```

% from: samples/sandbox/view/LocalInput.cpp
```cpp
    if (pushLatch) g.buttons |= kButtonPush;
```

## 4. Read the bit in the simulation

`sim/` turns the bytes into what the game means, for every player the same way:

% from: samples/sandbox/sim/Pawns.cpp
```cpp
    i.push = (in.buttons & kButtonPush) != 0;
```

A new input changes the tick input everyone sends, so all players need the same game version: the simulation version changes with the code, and peers with another version are refused.
