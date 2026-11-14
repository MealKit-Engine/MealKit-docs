# Editor

The general-purpose editor `MealKitEditor` runs the game in play mode, edits tuning, tables and other data, and builds game code and releases. Scenes are edited in MkRender ({doc}`scene_editor`); the editor shows the open scene read-only and plays it. The first steps are in {doc}`../getting_started/editor_quick_start`.

## Controls

| Control | Action |
|---|---|
| Right drag + `WASD` / `Q` `E` | Fly the camera (`Shift` for faster, wheel to change speed) |
| Wheel / middle drag | Move forward and back / pan |
| `Ctrl+S` | Save data (tuning, tables, project settings) |
| `Ctrl+O` | Open a scene to look at and play |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo in the Data window |
| `F5` | Play / back to editing (`Esc` goes to the game, for its pause menu) |
| `Ctrl+R` / `Ctrl+B` | Build game code (hot reload) / release build. If the engine changed while the editor is open, the build can't replace the engine the editor is using: the editor offers **Save, Restart and Rebuild**, which closes it, builds the engine in a console window and opens the project again |
| `Ctrl+T` | Show or hide the Tables panel |

## Panels

- **Layout**: **Previews** is on the right, and **Debug** and assets share a strip under the viewport. **Window > Layout** picks Edit, Play or Look Dev and resets the layout.
- **Asset grid**: the slider at the top of **Assets** switches from the list to a grid with model pictures.
- **Command palette**: Ctrl+P finds commands, scenes, tools, assets, table rows and tuning values. Letters can have gaps, and Korean initial consonants work.
- **Compact rows**: **Preferences > Interface** tightens rows so more fits on small screens.
- **Viewport tab**: the viewport is a tab. Drag other windows, such as **Data**, next to it to switch between them, or dock it elsewhere. It can't float: let go outside a dock and it returns to the center. Starting play brings it to the front.
- **Settings**: **Project > Settings...** gathers project settings, preferences, tools and keyboard shortcuts under one list. Modules have their own window, **Window > Modules** (see {doc}`modules`).
- **Previews**: **Window > Previews** has Look Dev and cutscene tabs. Game screens have their own **UI** tab beside the viewport (see {doc}`ui`).
- **Unsaved list**: when something is unsaved, click `Unsaved: N` in the status bar to save or revert each document.
- **Table views**: on a table page, filter rows, click a column header to sort, and edit the chosen row in the list below. Sorting only changes the view, not the file.
- **Find Uses**: right-click a file in **Assets** to list the text files that name it.
- **Saved layouts**: **Window > Layout** saves the current layout under a name. The **Window** menu also turns panels on and off; playing reopens the viewport.
- **State graphs**: on the **State** page of **Debug**, add a field path to graph it while playing.
- **Log**: **Window > Debug**, Log page, shows engine and game log lines, with what is wrong right now above them: missing models, models over budget and missing row references. Click a problem to open the document (objects are fixed in MkRender); the flag button shows or hides the list. The info, warning and error buttons filter the lines, the search box finds a line, and the trash button empties the log.
- **Notices**: messages also appear at the bottom right of the viewport. Failures stay until you close them; click one to open the build log or the log. While playing, the menu bar turns brown and the viewport gets an orange frame.
- **Command palette**: press Ctrl+P (or **Window > Command Palette**) and type part of a command, scene or tool name, in English or Korean. Use the arrow keys and Enter to run it.
- **Preferences**: **Project > Settings, Preferences page** sets the camera speed, text size, autosave interval and code editor. The window layout is kept per project in `build\editor\layout.ini`. Press F1 for the list of keyboard shortcuts.
- **Viewport toolbar**: the row along the top of the viewport switches the floor grid, perspective or orthographic, the view mode and the camera speed. Click the axis cube at the top right of the picture to look from that side.
- **Status bar and project list**: the open scene's name (with `*` when unsaved) is at the left of the status bar; click it to open another scene from the project. **Project > Project Manager** opens MealKit Manager (or the editor's own project list) next to the editor.
- **Camera**: the wheel moves toward the point under the mouse, and the toolbar switches between perspective and orthographic. Ctrl+1 to Ctrl+9 save camera bookmarks for the scene; 1 to 9 go back to them.
- **Performance**: **Window > Debug**, Performance page, (or click the fps number in the status bar) graphs the CPU and GPU frame time, simulation tick, draw calls and network traffic of the last 30 seconds against the budgets in the roadmap. Values over budget turn red.
- **Jump to code**: click a blue `file(line)` line in the build log or the log to open it in the code editor set in Preferences (VS Code by default).
- **Scenes**: **Scene > Scenes** lists the scenes in `assets/scenes`. The star marks the start scene; select another and press **Set as Start Scene** to change it in `mealkit.project`, or **Open in MkRender** to edit it. **File > Recent Scenes** reopens the scenes you used last in this project.
- **Play from here**: Shift+F5 (the list by the play button) starts a solo game with the player under the editor camera. MkRender asks for the same from its own camera ({doc}`scene_editor`). The scene file does not change.
- **Assets**: the **Assets** tab under the viewport shows the `assets` folders and files. Double-click a scene to open it in MkRender (or here without MkRender); pick a model to show it in Look Dev. Right-click a file and choose **Rename or Move** to change its path; references in scenes, tuning, UI and table files are updated too.
- **Data**: **Window > Data** gathers tuning, tables, feedback and sounds under one list, with `*` on unsaved documents. **Undo** and **Redo** on the page, or Ctrl+Z and Ctrl+Y while the window has focus, step back through its edits, including deleted rows and reloads. Particle effect files have no undo.
- **Debug**: **Window > Debug** gathers Log, Build Log, Performance and State under one list, with the problem count on its tab.
- **Tuning** (a Data page): two pages. Game holds the values the simulation reads (`assets/game.tuning`); during solo play changes apply at once. Display holds the values that are only seen (`assets/view.tuning`); changes apply at once in every player window, even with several players.
- **Tuning presets (A/B)**: the **+** button saves the current values as a preset, `assets/game.<name>.tuning` beside the file (**Balance** can compare it in bot matches). Pick a preset (or **(file)**) for **A** and **B**, then **Show A** / **Show B** puts that set's values in place; while playing they apply at once, so two feels can be tried back to back. **Compare with: File** marks the fields that differ from the saved file instead of from the defaults, and **Only changed** then lists just those.
- **Tables** (a Data page): the game's definition tables (`assets/tables/*.table`) and the engine's input bindings table as a spreadsheet, CSV import and export. Playing saves edited tables first.
- **Sounds** (a Data page): output buses, playing voices and culled plays, and a preview of sound events (see {doc}`sound`).
- **Feedback** (a Data page): the feedback table that turns tick events into sounds, camera shake, screen flash and hit stop (see {doc}`sound`).
- **UI**: previews a game screen (`assets/ui/*.ui`) over the viewport with test view model values (see {doc}`ui`).
- **State** (a Debug page): the simulation state declared with `MEALKIT_FIELD` while playing.
- **Project Settings**: `mealkit.project` (Project > Settings).
- **Folder layout**: when a project opens, the editor runs the layout check in the background and lists misplaced files (see {doc}`projects`).
- **Build**: the Build menu runs the project's `build.bat Editor` and `build.bat Export` in the background and shows the log.
- **Tools**: the Tools menu opens the installed MealKit tools (separate programs such as the audio tool) with this project (see {doc}`tools`).

## View modes

The **View Mode** list on the viewport toolbar colors the viewport by what costs time, so artists can see what is expensive:

| Mode | Shows |
|---|---|
| Lit | The normal picture |
| Wireframe | The triangle edges |
| Normals | The surface direction as a color |
| LOD Level | The level of detail drawn: green = full, yellow = level 1, red = level 2 |
| Overdraw | How many times each pixel is drawn, with no depth test: brighter means more layers |
| Over Budget | Models over their asset budget in red, everything else gray ({doc}`assets`) |
| Material Features | The style features of each material: outline red, wind green, rim blue, dissolve yellow (colors add up when a material has several), none gray ({doc}`assets`) |

View modes apply to the scene view and are left out of shipped builds.

## Look dev

**Window > Previews** opens a window that shows the model picked in **Assets** on a turntable, lit the same way whatever the scene's lighting is. Use it to check a model and its materials right after exporting from Blender.

- **Light**: four fixed light setups (neutral studio, daylight, sunset, night), then every sky HDRI under `assets/textures/` ({doc}`assets`).
- **Lighting model**: the project setting, or `Pbr`, `Toon` or `Unlit` to compare looks without changing the project.
- **Turn**, **Zoom**: the turntable spins by itself; drag the picture to turn it and change the height, and use the mouse wheel to zoom.
- **Flash**, **Dissolve**: preview the per-object values that game code sets ({doc}`assets`).

The window follows the model picked in **Assets**; picking another file keeps the last model. `--lookdev` opens it at start (`--lookdev-model <model>` picks the model).

## GPU capture

For graphics programmers: start the editor (or a development game exe) with `--gpu-capture` and the engine loads **RenderDoc** (Direct3D 12 and Vulkan) or **PIX** (Direct3D 12) if one is installed. **View > GPU Capture** or `F11` then captures the next frame; with RenderDoc, the RenderDoc window opens with the capture. Captures go to `%LOCALAPPDATA%\MealKit\gpu-captures`.
Without `--gpu-capture` or without an installed tool, the menu item is hidden. The tool has to be loaded before the graphics device is created, which is why it is a start option.

## Play mode

Play mode runs the game inside the editor with the open scene, as saved (MkRender saves before it asks the editor to play). It can run several players at once, pause, and rewind.
For automated checks, the editor also runs from the command line (see {doc}`../reference/command_line`).

The list at the right end of the viewport's bar sets the play view size, like a game view's aspect list: **Free Aspect** fills the tab, and an aspect (16:9, 4:3, ...) or a resolution (1920x1080, ...) gives the game the largest rectangle of that shape, centred, with black bars around it. A resolution also shows the scale it is drawn at. While paused (`F6`) the game gets a frame time of 0, so its presentation (animations, camera, UI timers) stops with the simulation; `F7` gives it the time of the tick it steps.

The button at the right end of the viewport's bar, a double click on the viewport's tab, or **Window > Maximize Viewport** makes the viewport fill the window, with the docked panels hidden (like a maximized game view); the same button, a double click on the bar, or the menu item brings the layout back. The panels keep their places.

How the editor works inside (game DLL loading, hot reload, play mode, rewind) is in {doc}`../engine_dev/internals/editor`.
