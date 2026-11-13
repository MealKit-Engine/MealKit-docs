# Scene editor (MkRender)

Scenes are edited in **MkRender**, a separate program built on the engine's renderer, the way screens are edited in the MkUI Designer and sound events in MkAudio. It opens a project's `.scene` files with a hierarchy, a viewport and an inspector, and saves them for the engine. The MealKit editor plays them ({doc}`editor`).

## Opening a scene

- In the MealKit editor: **Tools > MkRender** opens the project. **Scene > Open in MkRender**, **Open in MkRender** in **Scene > Scenes**, or double-clicking a scene in **Assets** opens that scene. Install MkRender like other tools ({doc}`tools`); without it, the editor opens the scene itself to look at and play.
- In MkRender: **File > Open project...** or **File > Project scenes**. A `.gltf`/`.glb` file opens in a new scene as one decoration, to look at a model.
- MkRender reads the project's object kinds from `build/editor/kinds.txt`, which the editor writes when it loads the game code (or `<game>_headless --write-kinds`). Field names, typed fields and the **Add** menu come from it; without it, game kinds' fields are edited as text.

## Controls

| Control | Action |
|---|---|
| Right drag / middle drag / wheel | Orbit / pan / zoom |
| Right drag + `WASD` / `Q` `E` | Fly the view (`Shift` for faster) |
| Left click | Select (Shift or Ctrl adds or removes; drag on empty space for a box) |
| `W` `E` `R` | Move / rotate / scale gizmo (hold `Ctrl` to snap) |
| `F` | Frame the selection |
| `Ctrl+D` / `Delete` | Duplicate / delete |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl+S` / `Ctrl+O` / `Ctrl+N` | Save / open / new scene |
| `H` / `Shift+H` | Hide the selection / show everything |
| `G` | Floor grid |
| `B` | Brush of the selected terrain or scatter layer |
| `End` | Drop the selection to the floor |
| `Ctrl+1` to `Ctrl+9` / `1` to `9` | Save / go to a camera bookmark (shared with the MealKit editor) |
| `F5` / `Shift+F5` | Play in the MealKit editor / play from here (below) |

## Objects

The object kinds come from the game (`MEALKIT_OBJECT` declarations) and appear in the **Add** menu. The example game has these:

- **Solid box**: visible and collides.
- **Decoration (no collision)**: only visible.
- **Spawn point**: where players start. Not visible in the game.
- **Match area** and **Box spawn area**: invisible area boxes. Their edges are drawn in the viewport.

Objects can carry a **model** (glTF): drag one from **Assets** into the viewport, or set the **Model** field. See {doc}`assets`. A skinned model plays the clip chosen in the inspector's **Clip** box (the object's `anim` field) in a loop; **View > Play animations** stops them.

Scenes are saved as human-readable `.scene` text: each object is its kind name plus field text. Values of child objects are relative to their parent. Drag an object onto another in the hierarchy to make it a child, and give objects a folder to group them.

**Edit > Arrange** lines up several selected objects (minimum, center or maximum on an axis) or spaces them evenly. Hidden and locked objects and camera bookmarks are kept per project in `build/editor`, not in the scene file.

## Prefabs

A prefab is a group of objects saved to a file so you can place it many times, like a lamp post with its light or a furnished room.

- **Save**: select the objects and choose **Edit > Save selection as prefab**. Their children are saved too. The file goes in `assets/prefabs/` as a `.prefab` text file.
- **Place**: drag a prefab from **Assets** into the viewport, or double-click it to place it at the view center.
- Placing makes plain copies, like Duplicate. Changing the prefab file later does not change copies already in scenes, and the game never reads prefab files.

## Terrain

A terrain is a heightmap stretched over its object's box: black is the bottom of the box, white the top. Players stand and collide on it, and it goes into the multiplayer content check like models.

- **Add**: **Add > Terrain**, then **New flat heightmap** in the inspector. The heightmap is saved to `assets/terrain/<scene>_<id>.png` when you save the scene.
- **Import**: make a heightmap in an external terrain tool (Gaea, World Machine, etc.), export a square 16-bit grayscale PNG into `assets/terrain/` and set it as the **Heightmap** field. The top of the image is the +z side.
- **Size**: the object's scale is the terrain size: x and z are the width and depth, y the height range. Rotation is ignored.
- **Brushes**: select the terrain, press `B` (or tick **Brush** in the inspector) and drag with the left mouse button. **Raise** and **Lower** push the ground, **Flatten** levels it to the height where the stroke started, **Smooth** softens it. **Radius** and **Strength** set the size and speed. Each stroke is one undo step; saving the scene writes the heightmap file.

### Scatter layers

A scatter layer paints thousands of copies of one model, such as grass, rocks or small props, onto terrain and floors. They are only for looks: players walk through them, and they are not part of the multiplayer content check.

- **Add**: **Add > Scatter layer**, then **New instance file** in the inspector. Set its **Model**, **Density** and size range.
- **Paint**: with the layer selected and the brush on, drag with the left mouse button. Copies land on whatever is below. Hold Shift (or pick **Erase**) to remove them. Each stroke is one undo step.
- The copies are saved to `assets/terrain/<scene>_<id>.scatter` when you save the scene. Make one layer per model.

## Sprites

A sprite is an image placed in the world, the way 2D games draw characters, backgrounds and props. Sprites are only for looks: they don't collide and are not part of the multiplayer content check.

- **Add**: drag a PNG from **Assets** into the viewport, or **Add > Sprite** and choose the **Image**.
- **Size**: the object's x and y scale are the width and height in meters. Set **Pixels per meter** instead to size it from the image.
- **Pivot**: the point of the image that sits at the object's position, from 0 to 1 (0.5, 0.5 is the centre; y 0 puts the feet on the position).
- **Sheets**: for an image with several frames in a grid, set **Columns, rows** in the inspector. The inspector shows the whole image with the grid; click a cell to show it (cells are counted from the top left, row by row).
- **Pivot buttons**: the 3 × 3 buttons under the sheet set the pivot to a corner, an edge or the centre, placed like the point they pick on the image.
- **2D projects**: a project made from the 2D template (`view2d true` in `mealkit.project`) opens in a flat front view of the x/y plane. The view doesn't turn: right drag pans, `W`/`S` move up and down, and the wheel zooms. The grid lies on the plane, the move gizmo has only x and y, and the rotate gizmo turns only around z.

## Hierarchy marks and handles

- **Kind icons**: each row in the hierarchy starts with an icon for its kind (box, model, spawn point, area, light, camera, probe, sprite, other game kinds) drawn in the object's color.
- **Problems**: a `!` after a name marks something MkRender can see is wrong: a model or image file that doesn't load, a sprite without an image, a kind the project doesn't have, a reflection probe that isn't baked. Red is an error, orange a warning; hover over the row for the reason. Field values (missing rows, required fields) are checked by the MealKit editor's **Debug** list, which knows the game's types.
- **Radius handles**: fields the game marks with `gizmo=radius` (for example a point light's **Range**) show as rings around the selected object with a round handle. Drag the handle to change the value (`Ctrl` snaps to the move step).

## Look Dev

The **Look Dev** tab beside the inspector shows one model on a turning stand under fixed lighting, apart from the scene's lighting: the model clicked in **Assets > Models**, or else the selected object's. Pick a light (Neutral studio, Daylight, Sunset, Night or a `.hdr` from the project) and a lighting model, and try the material's flash and dissolve. Drag the picture to turn the stand and tilt the camera; the wheel zooms.

## Environment

The **Environment** window edits the open scene's sun, sky, fog, sky HDRI and post processing ({doc}`assets`).

- **Sky HDRI**: pick a `.hdr` under `assets/textures/`. The first use bakes it into `build/cache/environments`, the same file the engine reads.
- **Reflection probes**: **Bake probes** (or **Bake this probe** in a probe's inspector) draws the scene in six directions from each probe and writes `assets/probes/<scene>_<id>.mkprobe`.
- **Color LUT** and **Grading capture**: the capture saves the view without the LUT to `art/grading/<scene>.png` with a neutral `neutral.cube`; grade both in an external tool and export a `.cube` into `assets/lut/`.

## Assets

The **Assets** window lists models, prefabs, images and scenes, with pictures of models and images (**Pictures**). Drag a file into the viewport to place it on the surface under the mouse; right-click it for **Find uses in this scene**.

## Playing

MkRender finds the project's running MealKit editor and uses its play view: **Editor > Play in editor** (`F5`) saves the scene and plays it there, **Play from here** (`Shift+F5`) starts a solo game from MkRender's camera (or at the selected spawn point), and **Stop** (`F5`) ends it. **Look through selected camera** shows a virtual camera's view in the editor, and **Preview** plays a cutscene there.

## Command line

| Option | Meaning |
|---|---|
| `--project <folder>` | Open a project |
| `--file <scene\|model>` | Open this file |
| `--select <id>[,<id>...]` | Select objects |
| `--frames <n>`, `--capture <png>` | Exit after n frames, saving a screenshot |
| `--check-scene <file>` | Read and write a scene in memory and report whether it comes back the same |
| `--check-terrain <png\|scatter>` | The same for a heightmap or scatter file |
| `--bake-probes`, `--grading-capture` | Bake every probe / save the grading capture once the scene is open |
| `--editor-play` | Ask the running editor to play the scene once it is found |
| `--render-golden <shots.txt> <folder>` | Draw the graphics regression views ({doc}`../engine_dev/testing`) |
