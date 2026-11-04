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
| `F5` | Play / back to editing (`Esc` goes to the game, for its pause menu) |
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

## Prefabs

A prefab is a group of objects saved to a file so you can place it many times, like a lamp post with its light or a furnished room.

- **Save**: select the objects and choose **Edit > Save as Prefab...** (or right-click in the scene tree). Their children are saved too. The file goes in `assets/prefabs/` as a `.prefab` text file. Positions are kept relative to the first selected object; heights above the floor stay as they are.
- **Place**: in the **Assets** tab, double-click a prefab to place it on the floor in front of the camera, or drag it into the scene view to place it where you drop it.
- Placing makes plain copies, like Duplicate. Changing the prefab file later does not change copies already in scenes, and the game never reads prefab files.
- A prefab holds only data: kinds, positions and field values. Behavior is game code; to reuse behavior with its objects, use a source module (see {doc}`modules`).

## Terrain

A terrain is a heightmap stretched over its object's box: black is the bottom of the box, white the top. Players stand and collide on it, and it goes into the multiplayer content check like models.

- **Add**: **+ Type... > Terrain** makes a flat 128 x 128 m terrain. Its heightmap is saved to `assets/terrain/<scene>_<id>.png` when you save the scene.
- **Import**: make a heightmap in an external terrain tool (Gaea, World Machine, etc.) and export a square 16-bit grayscale PNG into `assets/terrain/`. In the inspector's **Terrain** section, choose **Import PNG...**. The top of the image is the +z side.
- **Size**: the object's scale is the terrain size: x and z are the width and depth, y the height range. Rotation is ignored.
- **Brushes**: turn on **Brush** in the **Terrain** section and drag with the left mouse button in the scene view. **Raise** and **Lower** push the ground, **Flatten** levels it to the height where the stroke started, **Smooth** softens it. **Radius** and **Strength** set the size and speed. Each stroke is one undo step; saving the scene writes the heightmap file.
- If you re-export the PNG from the external tool while the editor is open, the terrain reloads (unless you have unsaved brush edits).

### Scatter layers

A scatter layer paints thousands of copies of one model, such as grass, rocks or small props, onto terrain and floors. They are only for looks: players walk through them, and they are not part of the multiplayer content check. Place large objects that need collision as normal objects instead.

- **Add**: **+ Type... > Scatter layer**. Set its **Model** field (or leave it empty for small boxes) and its **Density**, size range and **Draw distance**.
- **Paint**: with the layer selected and **Brush** on, drag with the left mouse button in the scene view. Copies land on whatever is below: terrain, boxes or models. Hold Shift (or pick **Erase**) to remove them. Each stroke is one undo step.
- The copies are saved to `assets/terrain/<scene>_<id>.scatter` when you save the scene. Make one layer per model.

## Panels

- **Layout**: the scene tree is on the left, the inspector on the right, and **Debug** and assets share a strip under the scene view. **View > Layout** picks Edit, Play or Look Dev and resets the layout.
- **Scene tree folders**: right-click an object and choose **Move to Folder...**, or drag it onto a folder. A path like `Props/Trees` makes folders inside folders. Right-click a folder to rename or remove it. Folders are saved in the scene and do not affect game results. A `!` after a name marks a problem (hover for the reason), and a blue dot marks fields changed from the kind's defaults.
- **Several objects**: with objects of the same kind selected, changing a field in the inspector changes it on all of them. Fields that differ show a dash.
- **Asset grid**: the slider at the top of **Assets** switches from the list to a grid with model pictures.
- **Command palette**: Ctrl+P finds commands, objects, scenes, tools, assets, table rows and tuning values. Letters can have gaps, and Korean initial consonants work.
- **Handles in the scene view**: fields that have a size in the world, such as a point light's range, show circles and a handle around the selected object. Drag the handle to change the value.
- **Compact rows**: **Preferences > Interface** tightens rows so more fits on small screens.
- **Scene view tab**: the scene view is a tab. Drag other windows, such as **Data**, next to it to switch between them, or dock it elsewhere. It can't float: let go outside a dock and it returns to the center. Starting play brings it to the front.
- **Settings**: **File > Settings...** gathers project settings, preferences, modules, tools and keyboard shortcuts under one list.
- **Previews**: **View > Previews** has UI, Look Dev and cutscene tabs.
- **Unsaved list**: when something is unsaved, click `Unsaved: N` in the status bar to save or revert each document.
- **Scene environment**: select the **Scene** row at the top of the scene tree. The inspector then shows the sun, sky, fog, sky HDRI and post processing of the open scene.
- **Log**: **View > Debug**, Log page, shows engine and game log lines. Tick Info, Warnings or Errors to filter, type in the search box to find a line, and press Clear to empty it.
- **Notices**: messages also appear at the bottom right of the scene view. Failures stay until you close them; click one to open the build log or the log. While playing, the menu bar turns brown and the scene view gets an orange frame.
- **Command palette**: press Ctrl+P (or **View > Command Palette**) and type part of a command, object, scene or tool name, in English or Korean. Use the arrow keys and Enter to run it.
- **Preferences**: **File > Preferences** sets the camera speed, text size, autosave interval and code editor. The window layout is kept per project in `build\editor\layout.ini`. Press F1 for the list of keyboard shortcuts.
- **Scene tree**: type in the box above the tree (Ctrl+F) to find objects by name or type. The eye and lock buttons on the right of a row hide an object in the scene view or stop it being picked there; they are saved per project in `build\editor`, not in the scene file.
- **Multi-select**: Shift-click in the scene tree or the scene view to add or remove objects, drag a box in an empty part of the scene view, or press Ctrl+A. The gizmo then moves, rotates or scales all of them, and Duplicate and Delete act on all of them. The inspector edits the last object you picked.
- **Viewport toolbar**: the bar at the top left of the scene view switches between move, rotate and scale, local and world axes, snapping, the floor grid, the view mode and the camera speed. Click the axis cube at the top right to look from that side.
- **Snap and align**: set the move, rotate and scale snap steps in Preferences or with the arrow next to Snap on the toolbar. **Edit > Drop to Floor** (End) puts the selection on the object below it, and **Edit > Align** lines up or evenly spaces several selected objects.
- **Camera**: Alt + left drag orbits around the selection, the wheel moves toward the point under the mouse, and the toolbar switches between perspective and orthographic. Ctrl+1 to Ctrl+9 save camera bookmarks for the scene; 1 to 9 go back to them.
- **Inspector**: sections fold. Right-click a field for Reset to Default, Copy Value and Paste Value; a blue dot marks values that differ from the default. The lock before Scale keeps the X, Y and Z ratio. **Edit > History** (Ctrl+H) lists the undo steps; click one to go back to it.
- **Performance**: **View > Debug**, Performance page, (or click the fps number in the status bar) graphs the CPU and GPU frame time, simulation tick, draw calls and network traffic of the last 30 seconds against the budgets in the roadmap. Values over budget turn red.
- **Jump to code**: click a blue `file(line)` line in the build log or the log to open it in the code editor set in Preferences (VS Code by default). For a game object type, **Open Code** in the inspector opens its `MEALKIT_OBJECT` declaration.
- **Scenes**: **File > Scenes** lists the scenes in `assets/scenes`. The star marks the start scene; select another and press **Set as Start Scene** to change it in `mealkit.project`. **File > Recent Scenes** reopens the scenes you used last in this project.
- **Play from here**: Shift+F5 (**Build > Play From Here**) starts a solo game with the player under the editor camera, or at the selected spawn point. The scene file does not change.
- **Assets**: the **Assets** tab under the scene view shows the `assets` folders and files. Drag a model or prefab into the scene view to place it, or double-click a scene to open it. Right-click a file and choose **Rename or Move** to change its path; references in scenes, tuning, UI and table files are updated too.
- **Data**: **View > Data** gathers tuning, tables, feedback and sounds under one list, with `*` on unsaved documents. **Undo** and **Redo** on the page, or Ctrl+Z and Ctrl+Y while the window has focus, step back through its edits, including deleted rows and reloads. Particle effect files have no undo.
- **Debug**: **View > Debug** gathers Log, Problems, Build Log, Performance and State under one list, with the problem count on its tab.
- **Problems** (a Debug page): missing models, models over budget and missing row references in one list, with the count on the tab. Click a line to select the object or open the document.
- **Tuning** (a Data page): two pages. Game holds the values the simulation reads (`assets/game.tuning`); during solo play changes apply at once. Display holds the values that are only seen (`assets/view.tuning`); changes apply at once in every player window, even with several players.
- **Tables** (a Data page): the game's definition tables (`assets/tables/*.table`) and the engine's input bindings table as a spreadsheet, CSV import and export. Playing saves edited tables first.
- **Sounds** (a Data page): output buses, playing voices and culled plays, and a preview of sound events (see {doc}`sound`).
- **Feedback** (a Data page): the feedback table that turns tick events into sounds, camera shake, screen flash and hit stop (see {doc}`sound`).
- **UI**: previews a game screen (`assets/ui/*.ui`) over the scene view with test view model values (see {doc}`ui`).
- **State** (a Debug page): the simulation state declared with `MEALKIT_FIELD` while playing.
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
