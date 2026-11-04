# Editor

This page explains how the editor works inside: which files it loads, how game code is swapped while it runs, and what happens when you press Play.
How to use the editor is in {doc}`../../manual/editor`. The editor code is in {engine}`engine/src/mealkit/editor`.

## Three files

The Editor build (`build.bat Editor`) makes the engine and the editor, and each project builds only its game code against them:

```text
build\Editor\bin\mealkit.dll         the whole engine (renderer, physics, network, sound, Dear ImGui)
build\Editor\bin\MealKitEditor.exe   the general-purpose editor (scene editing, play mode, builds)
<project>\build\Editor\bin\<name>_game.dll   the project's game code (sim/, view/, app/)
```

The editor contains **no game logic**. Everything it knows about a game (object kinds, tuning, tables, events, view models) comes from the game DLL at run time.

The three files use the dynamic CRT so that they share one heap and one copy of Dear ImGui. The shipped game is different: one static exe with the static CRT and no editor.
Because the two builds use different CRTs and library forms, they live in separate folders (`build\Editor` and `build\Release`).
`mealkit.dll` exports every symbol through a generated `.def` file ({engine}`cmake/FixExportsDef.cmake`), so engine headers must not hold global variables that game code uses directly.

## Starting up

1. Without `--project`, the editor shows the project manager. When you choose a project, it starts **a new editor process** with `--project <folder>` and closes itself, so every project starts from a clean state.
2. With a project, it reads `mealkit.project` and calls `setProjectRoot()`, so asset lookups (`findAsset`) stay inside that project.
3. It loads the game DLL. If the DLL is missing or older than the engine, it builds the game code first (`build.bat Editor`) and loads the DLL when the build finishes.

"Older than the engine" compares the game DLL time with the engine import library `mealkit.lib` and every engine header outside `editor/`.
The time of `mealkit.dll` itself is not used: it changes whenever any engine `.cpp` changes, while the import library changes only when the exports change, which is exactly when the game DLL must be linked again. Headers are checked because a changed struct layout or inline function needs a recompile even when the exports stay the same.

## The game module boundary

A game DLL exports one function, `mealkitGetGameModule`, written by the macro `MEALKIT_GAME_MODULE("Name", GameSession)`. It returns a `game::GameModule` table ({engine}`engine/src/mealkit/game/GameInstance.h`):

| Entry | Used by |
|---|---|
| `apiVersion` | The editor refuses a DLL whose version differs from the engine's `kApiVersion` and asks you to rebuild the game code. |
| `create` / `destroy` | Play mode creates one `GameInstance` per match. The DLL deletes it, so memory goes back to the same heap. |
| `objectTypes` | The Add menu and the inspector (`MEALKIT_OBJECT` declarations). |
| `tuningType` / `viewTuningType` | The Tuning panel edits `assets/game.tuning` and `assets/view.tuning` with these types. |
| `projectSettingsType` | The game's `game.*` lines in Project Settings. |
| `tables` | The Tables panel and the content hash (`MEALKIT_TABLE`). |
| `eventType` | The Feedback panel shows the tick event kinds and fields. |
| `viewModels` | The UI panel previews screens with test view model values (`MEALKIT_VIEWMODEL`). |

The editor never sees game structs as C++ types. It reads their field declarations (`reflect::TypeInfo`) and draws them with one widget set, `editor::drawFields` ({engine}`engine/src/mealkit/editor/FieldEditor.h`).
The inspector, the Tuning panel, the Tables panel and the State panel all use it, so a new `MEALKIT_FIELD` appears in every panel without editor code.

A field label can carry display hints after the name: `"Push radius|Description|group=Pushing|range=0..30|step=0.1|unit=m|pick=effects:.fx"`. `group` starts a collapsible section, `range` gives a slider, `unit` follows the number, and `pick` gives a searchable list (`sound` for sound events, or `<folder>:<extension>` for files under `assets`). Labels stay out of the content hash, but editing a label in `sim/` still changes the simulation version, which hashes those source files.

The engine side of the game code boundary (`GameInstance`, `GameContext`) is described in the engine repository's {engine}`docs/CODING_MODEL.md`.

## Hot reload

`editor::GameModuleHost` ({engine}`engine/src/mealkit/editor/GameModuleHost.cpp`) never loads the built DLL itself. It copies it to `build\Editor\bin\hot\<name>.<process id>.<number>.dll` and loads the copy.
Windows locks a loaded DLL, so loading the original would stop the linker from writing a new one while the editor is open.
The process id is in the name because player windows of multiplayer play are separate processes that load their own copies.

A reload starts in two ways:

- A game code build started from the editor (`Ctrl+R`) finishes successfully.
- The DLL was rebuilt outside the editor (for example from VS Code). Every 0.5 seconds the editor reads the file's write time, and reloads only when it sees **the same new time twice in a row**, so it does not copy a file the linker is still writing.

A reload happens **only in edit mode**. During play the running `GameInstance` still uses code from the old DLL, so the swap waits until you stop.

Reloading follows this order:

1. The editor clears every pointer it got from the old module (object types, tuning type, tables, ...). Values being edited (tuning, game project settings, tables) are kept as text.
2. The new copy is loaded and checked (`mealkitGetGameModule` exists, `apiVersion` matches).
3. Only then is the old DLL unloaded. If the new one fails, the old one stays and the status bar says so.
4. The editor takes the new types and puts the kept text back into them, so unsaved edits survive the swap even when fields were added or removed.

Old copies are deleted on the next load: all of this process's copies, and other processes' copies older than one minute.

## One frame

The editor runs one loop ({engine}`engine/src/mealkit/editor/EditorMain.cpp`). Each frame:

1. Collect window messages and input.
2. `Editor::update`: build the editor UI with Dear ImGui and handle editing input (gizmo, picking, shortcuts, undo).
3. In edit mode, check whether the game code should be reloaded.
4. Start or stop play when it was requested.
5. During play, `PlaySession::update` runs the network session and the game.
6. Update sound and feedback.
7. Fill the draw list: the game's view during play, otherwise the scene view.
8. Draw the 3D scene, then the game screen UI, the UI panel preview, and finally the editor UI on top.

## Scene editing

A scene is a list of entities. Each entity has a kind name, a parent, a transform, an optional model and the text of its fields ({engine}`engine/src/mealkit/scene/Scene.h`).
Because fields are stored as text by name, a scene still opens when the game DLL is missing or its types changed: the inspector shows the fields of an unknown kind as plain text and keeps them as they are.

- **Picking**: a click casts a ray from the camera through the mouse and tests it against each entity's box (the model bounds when it has a model). Area objects are hit only on their edges, so a click inside an area selects the object inside it.
- **Gizmo**: ImGuizmo moves, rotates and scales the selected entity. Values are stored relative to the parent.
- **Undo**: before each edit the editor captures a snapshot of the whole scene. While a drag or a text field stays active, only the first snapshot is kept, so one drag is one undo step. Up to 100 steps are kept.
- **Autosave**: when there are unsaved changes, the scene is written to `<scene>.autosave` every 90 seconds and when the editor closes. When you open a scene whose autosave is newer, the editor offers to recover it.

## Play mode

`editor::PlaySession` ({engine}`engine/src/mealkit/editor/PlaySession.cpp`) is one match in the editor. Play mode uses the same `LockstepSession`, `GameInstance` and `game::Frontend` as the shipped exe, so a match in the editor runs the same code as the real game.

When you press Play:

1. Unsaved tuning values are written to a temporary `play.tuning`, and edited tables are saved (the game reads tables from files when a match starts).
2. The editor asks the game DLL for a new `GameInstance`.
3. The game starts with the scene being edited, including unsaved changes. Its view is drawn inside the scene view, and it gets keyboard input only while no editor panel is using the keyboard.

### Playing alone

The session starts offline (`startOffline`): no sockets, but the same tick and input path as a network match.
Tuning changes from the Tuning panel apply to the running game at once.

### Several players

With 2 to 4 players, the editor becomes the host on port 27215 and starts the same `MealKitEditor.exe` again in player window mode (`--player-window --join 127.0.0.1:27215`), one process per extra player. This is like Unity's Multiplayer Play Mode. A player window takes the same game options as the shipped exe and runs the same loop, `game::runGame`; only the window title, a muted start, no player files and no Steam login differ (`game::GameRunOptions`).

- The scene being edited is saved to `build\Editor\play\play.scene`, and the player windows load that copy, so unsaved edits are included.
- Every player builds the same content hash from the scene, models, tuning, project settings and tables. A peer with different data is refused, as in a real match.
- Game tuning changes are **not** applied during multiplayer play, because peers would then simulate with different values and desync. Display tuning (`view.tuning`) is only seen, so the editor rewrites a copy that player windows read again (at most every 0.2 seconds).
- If the player windows do not connect within 30 seconds, play stops. Their logs are `build\Editor\play\player<n>.log`.

## Simulation debugging

During play the editor controls the simulation through `game::SimDebug` ({engine}`engine/src/mealkit/game/SimDebug.h`), implemented by `game::Simulation<World>`.

### Shadow simulation

With the shadow check on, the simulation runs a second `World` with the same inputs and compares the state hash every tick.
When they differ, the game pauses on that tick and the editor lists the `MEALKIT_FIELD` values that differ (`path: real -> shadow`). If no field differs, only the physics state differs.
This catches nondeterminism inside one process, without a second player.

### Pause, step and rewind

When playing alone, the simulation records every tick's inputs and state hash, and saves a snapshot every 150 ticks (5 seconds). It keeps 40 snapshots, about 3 minutes and 20 seconds.
`F6` pauses, `F7` steps one tick, and the timeline moves to any recorded tick.

To show a past tick, the simulation loads the nearest earlier snapshot and runs the recorded inputs up to that tick, comparing each tick's hash with the recorded one.
A mismatch means the state holds a value that is not declared with `MEALKIT_FIELD` (snapshots only save declared state) or that the code is not deterministic. The editor shows this as an error.
Rewind is off in multiplayer play, because one peer cannot pause the others.

## Builds from the editor

The Build menu runs the project's own scripts in the background with `ChildProcess` ({engine}`engine/src/mealkit/platform/Process.h`) and shows their output in the build log:

| Menu | Runs | Afterwards |
|---|---|---|
| Build Game Code (`Ctrl+R`) | `build.bat Editor` | The new game DLL is hot reloaded. |
| Release Build (`Ctrl+B`) | `build.bat Export` | The release folder `export\<name>` is ready. |
| Upgrade (offered when the project's engine version differs) | the engine's `tools\upgrade_project.ps1` | The game code is built again. |

When a project opens, the editor also runs the folder layout check (`tools\check_layout.ps1`) in the background and lists misplaced files.

## Editor UI

The editor UI is Dear ImGui with docking, drawn after the 3D scene by the same renderer. ImGui lives in `mealkit.dll`, so the game DLL draws its own debug windows (`GameInstance::debugUi`) into the same frame.
UI text is written in English in the code with `tr()`, `trl()` and `trf()`, and translations are in `engine/res/strings/<language>.txt` ({engine}`engine/src/mealkit/editor/Strings.h`). `trl()` keeps the English text as the window ID, so the docking layout stays the same when the language changes.

## Techniques used

The algorithms and patterns behind the parts above, with where to find them in the code.

### Scene view

| Technique | Where | What it does |
|---|---|---|
| Ray casting from screen coordinates | `Editor::handlePicking` | Turns the mouse position into normalized device coordinates and builds a ray from the camera's field of view, aspect ratio and axes. |
| Ray–oriented box test (slab method) | `rayBox` in `Editor.cpp` | Moves the ray into the box's local space with the inverse rotation, then intersects it with the three pairs of parallel planes (slabs). The ray hits when the entry distance is not greater than the exit distance. The nearest hit wins. |
| Edge-only picking for areas | `areaEdges` | An area box is tested as 12 thin boxes along its edges, so clicks inside it reach the objects within. |
| Matrix to position, rotation and scale | `decompose` in `Editor.cpp` | Scale is the length of each basis column. The rotation matrix becomes a quaternion with the trace method (Shepperd's method), which picks the largest diagonal term to stay numerically stable. |
| Gizmo | ImGuizmo `Manipulate` | Draws the move, rotate and scale handles and returns a new matrix, which the editor decomposes back into the entity transform (with optional snapping). |
| Reparenting in place | `Editor::reparent` | Keeps the world transform and computes the new value relative to the new parent, so the object does not move on screen. Moving an object under its own child is refused (a cycle check on the parent chain). |
| Level of detail by screen size | `ModelCache::pickLod` | Estimates how much of the screen a model covers (bounding radius divided by distance) and picks one of the LODs made by meshoptimizer. |
| Instanced drawing | `render::DrawList` | Collects instances per mesh and draws each mesh with one draw call. |

### Editing data

| Technique | Where | What it does |
|---|---|---|
| Run-time reflection | `reflect::TypeInfo`, `editor::drawFields` | Field declarations (`MEALKIT_FIELD`) describe names, types and offsets, so one generic widget set edits any game struct. |
| Text serialization by field name | `reflect::toText` / `fromText` | Values are saved as `name = value` text. Names a type no longer declares are reported in the log instead of failing the load, and while a type is unavailable (during hot reload) the values are kept as text. |
| Snapshot undo (memento) | `Editor::capture` / `restore` | Each undo step is a copy of the whole scene, taken once at the start of an edit. This is simple and always correct for scenes of this size, and the history is capped at 100 steps. |
| Virtualized lists | `ImGuiListClipper` in `FieldEditor.cpp` | Large pools in the State panel draw only the visible rows. |
| Immediate mode GUI | Dear ImGui | The whole editor UI is rebuilt from the current data every frame, so there is no widget state to keep in sync with the scene. |

### Game code and processes

| Technique | Where | What it does |
|---|---|---|
| Hot reload by copy | `GameModuleHost::load` | Loads a copy of the DLL so the original stays writable for the linker. The new module is loaded and checked before the old one is unloaded. |
| Debounced file watching | `GameModuleHost::sourceChangedAndStable` | Polls the write time and reacts only when it is the same twice in a row, so a file still being written is not used. |
| Versioned C ABI | `GameModule`, `kApiVersion` | The boundary is one `extern "C"` function returning a table of function pointers, checked with a version number. |
| One process per player | `PlaySession::start` | Multiplayer play starts the editor again as player windows that talk over real UDP on `127.0.0.1`, so the network path is the same as a real match. |

### Simulation and network

| Technique | Where | What it does |
|---|---|---|
| Deterministic lockstep | `net::LockstepSession` | Peers exchange only inputs and run the same simulation. Editor play uses an input delay of 3 ticks. |
| State hashing (FNV-1a) | `Hasher` in {engine}`engine/src/mealkit/core/Hash.h` | Hashes the declared state field by field (so struct padding never enters the hash). Equal hashes on the same tick mean equal states. |
| Content hash | `game::contentHash` | Hashes the scene's collision data, models, tuning, project settings and tables, so peers with different data are refused before a match. |
| Dual execution (shadow simulation) | `game::Simulation` | Runs a second copy of the world with the same inputs and compares hashes every tick to catch nondeterminism inside one process. |
| Structural diff | `reflect::diffStruct` | Walks two values of the same declared type and lists the fields that differ, shown when the shadow simulation diverges. |
| Checkpoints and replay | `game::Simulation::seek` | Periodic snapshots of the declared state and the Jolt physics state (`StateRecorder`) plus every tick's inputs. Seeking loads the nearest earlier snapshot and replays inputs, which costs far less memory than a snapshot per tick. |
| Ring buffer of history | `takeSnapshot` | Keeps the newest 40 snapshots and drops inputs older than the first one, so memory stays bounded. |

### Other

| Technique | Where | What it does |
|---|---|---|
| Source-string localization | `tr()` in {engine}`engine/src/mealkit/editor/Strings.h` | The English text is the key and a missing translation shows the English text, like gettext. `trl()` adds `###` with the English text so ImGui window IDs do not change with the language. |
| Background child processes | `ChildProcess` | Builds and checks run in hidden child processes whose output is read without blocking the editor frame. |
| Autosave with recovery | `Editor::updateAutosave` | Writes a side file instead of the scene, and compares file times on open to offer recovery after a crash. |
