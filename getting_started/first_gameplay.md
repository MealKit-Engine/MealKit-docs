# Your first gameplay change

This tutorial adds a **double jump** to a project made from the example ({doc}`first_project`). It goes through every place a rule touches: a tuning value, state fields, a system function, the editor, and the determinism checks.
How these parts fit together is explained in {doc}`../manual/game_code`.

Open the project in the editor (`editor.bat` in the project folder) and the project folder in VS Code ({doc}`workflow`).

## 1. Add a tuning value

How many extra jumps a character gets in the air is a game rule, so it goes in the tuning, not in code ({doc}`../manual/assets`, "Where numbers go").
In `source/sim/Tuning.h`, add a field next to the other movement values:

```cpp
MEALKIT_FIELD(mealkit::f32, jumpSpeed, 8.0f, "Jump speed (m/s)");
MEALKIT_FIELD(mealkit::u32, airJumps, 1, "Air jumps");
```

The last argument is the label the editor shows. `assets/game.tuning` does not need to change: a value missing from the file uses the default in the declaration.

## 2. Add state fields

The simulation must remember two things from one tick to the next: how many air jumps are left, and whether jump was already held on the last tick (so holding the key does not spend every air jump at once).
Values that live across ticks are state, so they are declared with `MEALKIT_FIELD` in the pawn, in `source/sim/World.h`:

```cpp
MEALKIT_STRUCT(Pawn) {
    // ...
    MEALKIT_FIELD(TickTimer, pushReady, {}, "Next push");
    MEALKIT_FIELD(u32, airJumpsLeft, 0, "Air jumps left");
    MEALKIT_FIELD(bool, jumpHeld, false, "Jump held");
    // ...
};
```

A plain member without `MEALKIT_FIELD` would compile and even seem to work, but it would be missing from the state hash, rewind and the shadow simulation, so desyncs it causes could not be found.

## 3. Change the system function

Jumping is in `movePawn` in `source/sim/Pawns.cpp`. Replace the jump block with:

```cpp
const bool jumpPressed = intent.jump && !p.jumpHeld; // pressed this tick, not held from the last one
p.jumpHeld = intent.jump;
if (p.grounded) p.airJumpsLeft = t.airJumps;
if (p.grounded && intent.jump && v.y < t.jumpMaxRise) {
    v.y = t.jumpSpeed;
    world.events.push(makeEvent(EventKind::Jump, player, p.position, 0.0f));
} else if (!p.grounded && jumpPressed && p.airJumpsLeft > 0) {
    --p.airJumpsLeft;
    v.y = t.jumpSpeed;
    world.events.push(makeEvent(EventKind::Jump, player, p.position, 0.0f));
}
```

- The rule reads only the state, the tuning and this tick's input (`intent`), so every peer computes the same result.
- The air jump pushes the same `Jump` tick event as a ground jump, so the jump sound and effects from the feedback table play with no view code. To give it its own sound, add a kind to `MEALKIT_ENUM(EventKind, ...)` and a row for it in the Feedback panel ({doc}`../manual/sound`).
- AI characters go through the same `movePawn`, so they follow the new rule too.

## 4. Build and try it in the editor

1. Press `Ctrl+R` in the editor (or `Ctrl+Shift+B` in VS Code). The game code is rebuilt and swapped in without closing the editor. Before the build, **SimCheck** checks `sim/`; if a rule is broken, the build stops with `error SIMnnn` and the line.
2. Open the Tuning panel: "Air jumps" is in the Game tab.
3. Press `F5` to play and press `Space` twice: the second jump happens in the air.
4. Open the State panel and look at a pawn: `Air jumps left` counts down in the air and comes back on landing. Pause play mode and step one tick at a time to watch it change.
5. Change "Air jumps" to 2 in the Tuning panel. During solo play the change applies at once; the panel's Save button writes it to `assets/game.tuning`.

## 5. Check determinism

Build the release game (`build.bat` in the project folder) and run the one-process check:

```bat
build\Release\bin\<name>.exe --bot --exit-tick 900 --shadow --rewind-test --vsync 0
```

It must print `SHADOW ok` and `REWIND ok`. Then run the multiplayer test with several peers from the engine folder (in VS Code: `Tasks: Run Task` → `Multiplayer Determinism Test`):

```powershell
powershell -ExecutionPolicy Bypass -File tools\mp_test.ps1 -Exe <project>\build\Release\bin\<name>.exe -Clients 3 -Ticks 900
```

It must print `PASS`.

## What changed for players

- The new tuning value is part of the **content hash**, and the changed `sim/` code changes the **simulation version**. A player with an older build or older data is refused when joining, with the reason (see {doc}`../manual/multiplayer`).
- Input recordings made before the change no longer replay the same match. If the project keeps recordings for checks, record them again.

## Next steps

- Show the remaining air jumps on the HUD: add a field to the HUD view model and bind it in `assets/ui/hud.ui` ({doc}`../manual/ui`).
- Give each character body its own number of air jumps: add a column to the bodies table and read it with `bodyOf(world, player)` instead of the tuning value ({doc}`../manual/assets`, "Definition tables").
