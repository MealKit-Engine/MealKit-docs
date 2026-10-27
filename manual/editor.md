# Editor

The general-purpose editor `MealKitEditor` edits scenes, runs the game in play mode, and builds game code and releases. The first steps are in {doc}`../getting_started/editor_quick_start`.

## Controls

| Control | Action |
|---|---|
| Right drag + `WASD` / `Q` `E` | Fly the camera (`Shift` for faster, wheel to change speed) |
| Wheel / middle drag | Move forward and back / pan |
| Left click | Select (click empty space to deselect) |
| `W` `E` `R` | Move / rotate / scale gizmo (hold `Ctrl` while dragging to snap) |
| `F` or double-click in the scene tree | Move the camera to the selected object |
| `Ctrl+D` / `Delete` | Duplicate / delete |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl+S` / `Ctrl+O` / `Ctrl+N` | Save / open / new scene |
| `F5` / `Esc` | Play / back to editing |
| `Ctrl+R` / `Ctrl+B` | Build game code (hot reload) / release build |
| `Ctrl+T` | Show or hide the Tables panel |

## Objects

The object kinds come from the game (`MEALKIT_OBJECT` declarations) and appear in the editor's Add menu. The example game has these:

- **Solid box**: visible and collides.
- **Decoration (no collision)**: only visible.
- **Spawn point**: where players start. Not visible in the game.
- **Match area** and **Box spawn area**: invisible area boxes. The editor draws their edges; click an edge to select one.

Solid boxes and decorations can carry a **model** (glTF): `+ Model` in the scene tree, or `Choose Model...` in the inspector. See {doc}`assets`.

Scenes are saved as human-readable `.scene` text: each object is its kind name plus field text. Values of child objects are relative to their parent.

## Panels

- **Layout**: the scene tree is on the left, the inspector on the right (with the **Tuning** and **State** tabs), and logs and tables share a strip under the scene view. **View > Layout** picks Edit, Play or Look Dev and resets the layout.
- **Scene environment**: select the **Scene** row at the top of the scene tree. The inspector then shows the sun, sky, fog, sky HDRI and post processing of the open scene.
- **Log**: **Build > Log** shows engine and game log lines. Tick Info, Warnings or Errors to filter, type in the search box to find a line, and press Clear to empty it.
- **Notices**: messages also appear at the bottom right of the scene view. Failures stay until you close them; click one to open the build log or the log. While playing, the menu bar turns brown and the scene view gets an orange frame.
- **Tuning**: two tabs. Game holds the values the simulation reads (`assets/game.tuning`); during solo play changes apply at once. Display holds the values that are only seen (`assets/view.tuning`); changes apply at once in every player window, even with several players.
- **Tables**: the game's definition tables (`assets/tables/*.table`) and the engine's input bindings table as a spreadsheet, CSV import and export, and the list of missing row references. Playing saves edited tables first.
- **Sounds**: output buses, playing voices and culled plays, and a preview of sound events (see {doc}`sound`).
- **Feedback**: the feedback table that turns tick events into sounds, camera shake, screen flash and hit stop (see {doc}`sound`).
- **UI**: previews a game screen (`assets/ui/*.ui`) over the scene view with test view model values (see {doc}`ui`).
- **State**: the simulation state declared with `MEALKIT_FIELD` while playing.
- **Project Settings**: `mealkit.project` (File > Project Settings).
- **Folder layout**: when a project opens, the editor runs the layout check in the background and lists misplaced files (see {doc}`projects`).
- **Build**: the Build menu runs the project's `build.bat Editor` and `build.bat Export` in the background and shows the log.
- **Tools**: the Tools menu opens the installed MealKit tools (separate programs such as the audio tool) with this project (see {doc}`tools`).

## View modes

**View > View Mode** colors the scene view by what costs time, so artists can see what is expensive:

| Mode | Shows |
|---|---|
| Lit | The normal picture |
| Wireframe | The triangle edges |
| Normals | The surface direction as a color |
| LOD Level | The level of detail drawn: green = full, yellow = level 1, red = level 2 |
| Overdraw | How many times each pixel is drawn, with no depth test: brighter means more layers |
| Over Budget | Models over their asset budget in red, everything else gray ({doc}`assets`) |
| Material Features | The style features of each material: outline red, wind green, rim blue, dissolve yellow (colors add up when a material has several), none gray ({doc}`assets`) |

View modes apply to the editing view and are left out of shipped builds.

## Look dev

**View > Look Dev** opens a window that shows the model of the selected object on a turntable, lit the same way whatever the scene's lighting is. Use it to check a model and its materials right after exporting from Blender.

- **Light**: four fixed light setups (neutral studio, daylight, sunset, night), then every sky HDRI under `assets/textures/` ({doc}`assets`).
- **Lighting model**: the project setting, or `Pbr`, `Toon` or `Unlit` to compare looks without changing the project.
- **Turn**, **Zoom**: the turntable spins by itself; drag the picture to turn it and change the height, and use the mouse wheel to zoom.
- **Flash**, **Dissolve**: preview the per-object values that game code sets ({doc}`assets`).

The window follows the selection; selecting an object without a model keeps the last model. `--lookdev` opens it at start (with `--select`).

## GPU capture

For graphics programmers: start the editor (or a development game exe) with `--gpu-capture` and the engine loads **RenderDoc** (Direct3D 12 and Vulkan) or **PIX** (Direct3D 12) if one is installed. **View > GPU Capture** or `F11` then captures the next frame; with RenderDoc, the RenderDoc window opens with the capture. Captures go to `%LOCALAPPDATA%\MealKit\gpu-captures`.
Without `--gpu-capture` or without an installed tool, the menu item is hidden. The tool has to be loaded before the graphics device is created, which is why it is a start option.

## Play mode

Play mode runs the game inside the editor with the scene being edited. It can run several players at once, pause, and rewind.
For automated checks, the editor also runs from the command line (see {doc}`../reference/command_line`).

How the editor works inside (game DLL loading, hot reload, play mode, rewind) is in {doc}`../engine_dev/internals/editor`.
