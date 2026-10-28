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
- The boundary between the engine and game code is `mealkit::game::GameInstance` (`engine/src/mealkit/game/GameInstance.h`). The game implements it (engine services arrive as `GameContext&`) and exports the editor entry point with `MEALKIT_GAME_MODULE(name, class)`. The release exe's `main` belongs to the engine too: `app/main.cpp` is one line, `MEALKIT_GAME_MAIN(GameSession, Headless)`, and the engine handles the command line (`--help`), window, session, screen services and automated test output. When this contract changes, `kApiVersion` goes up and DLLs with another number are not loaded.
- The shipped exe uses the game class directly, so there is no DLL boundary cost.

The engine repository itself is also an example game project (top-level `mealkit.project`, code in `samples/sandbox`, assets in `assets/`). It is the template for new projects and the target of the engine determinism test (`tools\mp_test.ps1`).

## MealKit Manager

MealKit Manager is a separate hub app (repository MealKit-Manager) that lists your projects, the engines they use and the installed MealKit tools. It does not contain an engine, so one Manager works with every engine version.

- **Projects**: create a project (it runs the chosen engine's `tools\new_project.ps1`), import a folder, open it in its engine's editor, and upgrade it when the project's `engineVersion` is older than its engine. The list is the same recent and favorite list the editor keeps.
- **Engines**: the engines your projects point to (the `engine` line of `mealkit.project`) and folders you add. If an engine's editor is not built, the Manager builds it.
- **Tools**: tools with a `mealkit-tool.txt` manifest, opened with the selected project.

Install it with `build.bat install` in the MealKit-Manager folder (to `%LOCALAPPDATA%\MealKit\manager`). After that, starting the editor without a project (`editor.bat`) opens the Manager. Without it, the editor shows its own project manager; `MealKitEditor --builtin-manager` always does.

## Project settings

`mealkit.project` holds the project settings: `name`, `engine`, `engineVersion`, `scene`, `tickRate`, the input delay range, the art style (`lightingModel`, `toonRamp`, {doc}`assets`), and game entries (`game.*`). Edit them in the editor under File > Project Settings.

`version` is the game version players see (title screen, lobby, window title). It is part of the simulation version, so players with different versions cannot join each other; raise it when you ship a change. `exportVersionFolder` puts it in the release folder name.

`tickRate` is the number of simulation ticks per second: 30 (default) or 60. 60 makes controls and collisions finer but doubles the simulation CPU and the input packets, so it suits games with few moving objects. Time values in tuning, tables and scenes are written in seconds, so changing it needs no data changes; every player must use the same value (it is part of the content hash). The editor applies a new value from the next play.
To rename a project (the name is also the exe name), use the project manager or `tools\rename_project.ps1 -Project <folder> -Name <new name>`.

## Folder layout

The engine fixes the project layout, so tools find files without settings and source files never end up in a release.

| Folder | What goes there |
|---|---|
| `source/` | Game code (`sim/`, `view/`, `app/`) |
| `assets/` | Only what ships with the game. Directly inside it: the kind folders `scenes/ models/ textures/ sounds/ effects/ ui/ fonts/ tables/ strings/ lut/` and the fixed files `game.tuning`, `view.tuning`, `input.bindings`, `feedback.table`, `sounds.events`. Subfolders inside a kind folder are free |
| `art/` | Source files of external tools (`.blend`, Penpot, PSD, audio projects). Not shipped, not in the content hash |
| `modules/` | Source modules, one folder per module ({doc}`modules`) |
| `third_party/` | The game's own libraries: one folder per library with its original `LICENSE` and a `mealkit.txt` |
| `build/`, `export/` | Generated |

`tools\check_layout.ps1 -Project <folder>` checks the layout: unknown files directly in `assets/`, wrong extensions in kind folders, source formats in `assets/`, and libraries without metadata or with a license outside the allowed list.
`check.ps1`, the release build and the editor use the same script. New projects get every folder, and `upgrade_project.ps1` adds missing ones.

### Third-party libraries

Copy only the files needed to build into `third_party/<lib>/`, keep its `LICENSE`, and write `mealkit.txt` with `name`, `version`, `license`, `source`, `usedIn` and `kept`. If the library has a `CMakeLists.txt`, also give the target to link with `cmakeTarget`; otherwise it is used as headers only (`include` names the header folder).
`mealkit_add_game()` links these libraries into the game exe and DLL only. `sim/` code cannot include their headers (SimCheck `SIM011`), and a library the engine already has cannot be added again.
The release build merges the notices of MealKit itself, the engine libraries inside the exe, the game libraries and the fonts in `assets/fonts/` into `THIRD_PARTY_NOTICES.txt`, and fails if the exe is larger than 5 MB.
In the engine repository, `tools\gen_notices.ps1` builds `third_party/VERSIONS.txt` and `THIRD_PARTY_NOTICES.txt` from the same metadata.

## Game code folders

Game code is split into three folders. `mealkit_add_game()` collects them by pattern, so adding a file needs no CMake change.

| Folder | What goes there |
|---|---|
| `sim/` | Deterministic simulation. System functions take only `World&` and `World::step()` calls them in order. SimCheck checks this folder at build time |
| `view/` | Camera, input, drawing. Reads the `sim/` state but never changes it |
| `app/` | `GameSession` (the `GameInstance` implementation), `main.cpp` (`MEALKIT_GAME_MAIN`), `GameModule.cpp`, `Headless.cpp` |

The rules for `sim/` are in the engine's {engine}`coding model <docs/CODING_MODEL.md>` ("Determinism rules"). See also {doc}`multiplayer`.
