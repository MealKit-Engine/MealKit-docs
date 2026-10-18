# Engine folder and game projects

Like Godot, **one general-purpose editor** opens many **game project folders**. Game code is C++, and the editor loads a project's game code as a DLL.

| Folder | What | What you do there |
|---|---|---|
| The engine folder (the engine repository, for example `D:\MealKit`) | The engine (`engine/`), the general-purpose editor `MealKitEditor.exe`, third-party libraries, shared build settings (`cmake/`), tools, the example game `samples/sandbox` | Engine and editor development, determinism tests |
| A game project folder (for example `D:\GameEngine\MealKit\<game>`) | `mealkit.project`, game code (`source/`), assets (`assets/`), builds (`build/`), **the release (`export/<game>/`)** | Making the game |

There are two kinds of builds:

| Build | Result | Used for |
|---|---|---|
| `build.bat Editor` | Engine: `mealkit.dll` + `MealKitEditor.exe` / project: `<game>_game.dll` (game code only, a few seconds) | The editor. Dynamic CRT, optimized with debug info |
| `build.bat` (Release) | One `<game>.exe` (engine linked statically, static CRT) | Release, determinism tests |

- The editor loads a **copy** of the game DLL, so you can rebuild game code while the editor is open. When a new DLL appears, the editor **swaps it in automatically in edit mode (hot reload)**.
- If the game DLL is missing or older than the engine (compared with the engine import library `mealkit.lib` and the newest engine header), the editor builds the game code first when it opens the project.
- The boundary between the engine and game code is `mealkit::game::GameInstance` (`engine/src/mealkit/game/GameInstance.h`). The game implements it (engine services arrive as `GameContext&`) and exports the editor entry point with `MEALKIT_GAME_MODULE(name, class)`. When this contract changes, `kApiVersion` goes up and DLLs with another number are not loaded.
- The shipped exe uses the game class directly, so there is no DLL boundary cost.

The engine repository itself is also an example game project (top-level `mealkit.project`, code in `samples/sandbox`, assets in `assets/`). It is the template for new projects and the target of the engine determinism test (`tools\mp_test.ps1`).

## Project settings

`mealkit.project` holds the project settings: `name`, `engine`, `engineVersion`, `scene`, and game entries (`game.*`). Edit them in the editor under File > Project Settings.
To rename a project (the name is also the exe name), use the project manager or `tools\rename_project.ps1 -Project <folder> -Name <new name>`.

## Game code folders

Game code is split into three folders. `mealkit_add_game()` collects them by pattern, so adding a file needs no CMake change.

| Folder | What goes there |
|---|---|
| `sim/` | Deterministic simulation. System functions take only `World&` and `World::step()` calls them in order. SimCheck checks this folder at build time |
| `view/` | Camera, input, drawing. Reads the `sim/` state but never changes it |
| `app/` | `GameSession` (the `GameInstance` implementation), `main.cpp`, `GameModule.cpp`, `Headless.cpp` |

The rules for `sim/` are in the engine's {engine}`coding model <docs/CODING_MODEL.md>` ("Determinism rules"). See also {doc}`multiplayer`.
