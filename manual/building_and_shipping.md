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
- Result: `export\<game>\` (or `export\<game>-<version>\` when `exportVersionFolder` is on in `mealkit.project`) with `<game>.exe`, `<game>.pak`, `build.txt`, `steam_api64.dll` and `THIRD_PARTY_NOTICES.txt` (plus `steam_appid.txt` when the app ID is 480). Distribute the whole folder.
- `build.txt` records the engine version, the project's git commit (with `+` when files were modified) and the content hash of the pack. `<game>.exe --help` prints it, and bug reports include it.

(pack-files)=
## Pack files

The release folder has no `assets` folder. The export first builds the development game (`build.bat`), then runs it with `--cook`, which converts the assets the game uses into engine formats and puts them into one pack file, `<game>.pak`:

- Models become ready-to-draw meshes with their LODs and compressed textures, cutscene cameras become baked keys, and sky HDRIs become the baked sky. The shipped game doesn't read glTF or compress textures, so it starts faster and the exe is smaller.
- Everything else (scenes, tables, UI, sounds, fonts) goes in as it is, compressed.

**What goes in**: only what the game reaches. The cook starts from the start scene, the scenes listed in **Other scenes to ship** (`scenes` in `mealkit.project`) and the data the engine always reads (tables, tuning, input bindings, sound events, feedback, effects, UI screens, strings, fonts). From there it follows paths: a scene brings in its models, prefabs, terrain and sky, `sounds.events` its clips, a `.ui` screen its images, and so on. Assets nothing references are left out, so unused files in `assets/` don't ship.

An asset that only your code names (for example a default value of a tuning field) can't be followed. List it, or a whole folder, in **Always put in the pack** (`packInclude`) in **File → Project Settings**. The cook warns about string literals in your code that name an asset it didn't pack:

```text
Cook: .../view/ViewTuning.h names assets/models/characters/rig_figure.glb, which nothing else references - not packed (add it to packInclude in Project Settings)
```

To check the cooked game without exporting, cook and play it from a development build:

```bat
build\Release\bin\<game>.exe --cook build\cook\<game>.pak
build\Release\bin\<game>.exe --pack build\cook\<game>.pak
```

With a pack, the game sees only what's in it, so a missing asset shows up here the same way it would for players. The editor always uses the files in `assets/`.

The executable size budget is 5 MB on every platform, without assets.
