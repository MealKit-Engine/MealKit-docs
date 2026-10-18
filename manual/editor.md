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

- **Tuning**: two tabs. Game holds the values the simulation reads (`assets/game.tuning`); during solo play changes apply at once. Display holds the values that are only seen (`assets/view.tuning`); changes apply at once in every player window, even with several players.
- **Tables**: the game's definition tables (`assets/tables/*.table`) and the engine tables (sound events, input bindings) as a spreadsheet, CSV import and export, and the list of missing row references. Playing saves edited tables first.
- **Sounds**: output buses, playing voices and culled plays, and a preview of sound events (see {doc}`sound`).
- **Feedback**: the feedback table that turns tick events into sounds, camera shake, screen flash and hit stop (see {doc}`sound`).
- **State**: the simulation state declared with `MEALKIT_FIELD` while playing.
- **Project Settings**: `mealkit.project` (File > Project Settings).
- **Folder layout**: when a project opens, the editor runs the layout check in the background and lists misplaced files (see {doc}`projects`).
- **Build**: the Build menu runs the project's `build.bat Editor` and `build.bat Export` in the background and shows the log.

## Play mode

Play mode runs the game inside the editor with the scene being edited. It can run several players at once, pause, and rewind.
For automated checks, the editor also runs from the command line (see {doc}`../reference/command_line`).
