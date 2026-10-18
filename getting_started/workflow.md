# Workflow (VS Code + editor)

Work in the **game project folder** when making a game, and in the engine folder when changing the engine.

1. **Open the editor**: the project's `editor.bat`, or the project manager. The first time takes a few minutes while the engine editor and the game code are built.
2. **Open the project folder in VS Code** (keep the editor open). When VS Code suggests the recommended extension (C/C++), install it.
3. Split the work like this:

| What you want to do | Where |
|---|---|
| Lay out the map (boxes, models, spawn points, lighting and fog) | Editor → `Ctrl+S` saves `assets/scenes/*.scene` |
| Game rules (movement, jumping, pushing, physics) | VS Code → the project's `source/sim/` (in the engine example, `samples/sandbox/sim/`). One file per system, run order in `World::step()` |
| Camera, controls, what is drawn on screen | VS Code → the project's `source/view/` (one match is run by `source/app/GameSession.cpp`) |
| Add engine or editor features | VS Code → `engine/src/mealkit/...` in the engine folder → `build.bat Editor` (close the editor first) |
| Make the game for release | Editor → Build → Release Build (`Ctrl+B`) → `export/<game>/` |
| Make 3D models | Blender → export glTF (.glb) into `assets/models/` |

4. **After changing game code**: VS Code `Ctrl+Shift+B` (build game code) or `Ctrl+R` in the editor. The editor swaps in the new code without closing.
5. **Debugging**: VS Code `F5` → `Editor (debug game code)` (game code inside the editor) or `Game (Debug)` (the shipped exe).
6. **Check multiplayer**: `Tasks: Run Task` → `Multiplayer Determinism Test` (it must print PASS).
