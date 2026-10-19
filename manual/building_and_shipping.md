# Building and shipping

## Build configurations

| Command | Folder | What it is for |
|---|---|---|
| `build.bat Editor` | `build\Editor` | The editor: engine `mealkit.dll` (dynamic CRT) + `MealKitEditor.exe`, and in a project only the game DLL `<game>_game.dll` |
| `build.bat` | `build\Release` | The development game: one static `<game>.exe` (static CRT) with the debug UI, plus `<game>_headless.exe` |
| `build.bat Debug` | `build\Debug` | Debugging, with the D3D12 debug layer |
| `build.bat Profile` | `build\Profile` | Release with Tracy markers (see {doc}`performance`) |
| `build.bat Export` | `build\Export` → `export\<game>\` | The release folder, built without the debug UI |

The Editor and Release builds use different CRTs and library kinds, so they live in separate folders.
The shipped exe stays a single static file and never links the editor. Dear ImGui is only in development builds and the editor (see {doc}`debug_ui`): the export builds the game again in its own folder with the debug UI turned off, so the first export takes longer.

(export)=
## Release build (export)

- In the editor: **Build → Release Build** (`Ctrl+B`). It builds in the background while the editor stays open and shows the log. Unsaved scenes are saved first.
- From the command line: `build.bat Export` in the project folder.
- Result: `export\<game>\` (or `export\<game>-<version>\` when `exportVersionFolder` is on in `mealkit.project`) with `<game>.exe`, `assets\`, `steam_api64.dll` and `THIRD_PARTY_NOTICES.txt` (plus `steam_appid.txt` when the app ID is 480). Distribute the whole folder.

The executable size budget is 5 MB on every platform, without assets.
