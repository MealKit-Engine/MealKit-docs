# Assets

## 3D models (glTF)

- Put `.glb` (recommended) or `.gltf` files under `assets/models/`. In Blender: File → Export → glTF 2.0, format glTF Binary.
- Scenes store model paths **relative to `assets/`**, like `models/tree.glb`.
- On load, meshoptimizer optimizes the vertex cache, overdraw and fetch order, and builds **two more LOD levels** for models with many triangles. Distant objects use the lighter LODs automatically.
- Materials are glTF PBR metallic-roughness, which is what Blender's Principled BSDF exports: base color, normal, metallic-roughness and emissive **textures and factors**, the vertex color (multiplied with the base color) and **alpha clip** (glTF alpha mode `MASK`). Other material features (clearcoat, transmission, sheen, alpha blend, double-sided, occlusion, a second UV set or texture transform) are ignored with a warning in the log.
- Textures inside the model (PNG or JPEG) are compressed once with mipmaps, to BC7 for color and BC5 for normal maps, and kept in `build/cache/textures` of the project. The first load of a new texture takes a moment; later loads read the cache. Delete the folder to rebuild it. The release build puts the compressed textures into the pack file (see {ref}`pack-files`).
- A solid box with a model collides as the **convex hull of the model's vertices** (concave parts are filled in). Hull points are taken from the original vertices before optimization, so they are the same on every PC.
- The sample models (tree, rock, ring, the textured `props/crate` and alpha-clipped `props/fence` used by `scenes/materials.scene`, and the `props/style_*` models of `scenes/styles.scene`) can be regenerated with `python tools/make_sample_models.py`.

## Art style: lighting model and material features

The look of a game is chosen, not programmed: games do not write shaders. There are three parts.

**Lighting model** (Project > Settings, `lightingModel`) sets the shading of the whole game:

| Value | Look |
|---|---|
| `Pbr` (default) | Physically based: soft diffuse light, glossy highlights that follow metallic and roughness |
| `Toon` | Flat bands of light and a hard highlight. The bands come from the **toon ramp** image (`toonRamp`, a path under `assets/`, like `textures/ramp.png`): its first row is read from left (the side away from the sun) to right (the lit side). Empty uses 3 grey steps. |
| `Unlit` | The colors as they are, with no light or shadow (fog still applies) |

The editor shows a new lighting model or a changed ramp image at once. Every lighting model is built into the game, so switching does not make the game stutter.

**Sky HDRI**: in MkRender's **Environment** window ({doc}`scene_editor`), **Sky HDRI** picks a `.hdr` image (an equirectangular HDR sky, for example a free CC0 one from Poly Haven) from anywhere under `assets/textures/`. The sky is drawn behind the scene, and the ambient light and the reflections on glossy and metal surfaces come from it. **HDRI intensity** scales all three and **HDRI rotation** turns the sky (degrees). The sun is still the scene's sun: point it where the sun is in the image. The first use of an image takes about a second to bake; the result is kept in `build/cache/environments`; the release build puts it into the pack file. Without an HDRI the sky and ground colors are used as before. `scenes/hdri.scene` uses the sample sky `textures/hdri/kloofendal_partly_cloudy_1k.hdr`.

**Reflection probes**: indoors or in shade, glossy surfaces should not reflect the open sky. Add a **Reflection probe** object (**Add** in MkRender) where the reflections should be seen from; its size is the box it affects (its edges in the viewport). Press **Bake this probe** in its inspector (or **Bake probes** in **Environment**): MkRender draws the scene in six directions from that point and writes `assets/probes/<scene>_<id>.mkprobe`, which you commit with the scene. Each object uses the probe whose box contains the object's position and whose center is nearest; objects outside every box reflect the sky HDRI. Probes do not blend and do not update while the game runs: bake again after changing the room. The project settings limit the probes per scene (**Reflection probes per scene**, default 8) and their size (**Reflection probe size**, default 128). Light brighter than white is clipped in a probe, because it is captured like the screen. `scenes/probes.scene` shows a mirror ball inside and outside a probe box; `MkRender --project <folder> --file <scene> --bake-probes` bakes from the command line.

**Point lights**: add a **Point light** object (**Add** in MkRender) for torches, lamps and other local light. Its fields are **Light color**, **Intensity** and **Range (m)** (the light fades to nothing at that distance); the editor shows it as a small box in its color. Each object takes the strongest lights that reach it, 4 by default (**Point lights per object** in the project settings, up to 8). Point lights cast no shadows. Game view code can also add short lights, such as an explosion flash, to `FrameParams::lights` for a few frames (the sandbox lights up every push). `scenes/lights.scene` shows three colored lights at night.

**Sun shadows**: the scene's sun casts soft shadows up to **Shadow distance** (40 m) from the camera, fading out at the end. The project settings choose **Shadow cascades** (2: a sharp map near the camera and a coarser one further away, or 1 for the cheapest) and **Shadow map size** (1024 px per cascade); **Sun shadows** turns them off. Every visible object casts and receives them, including alpha-masked holes; point lights do not cast shadows. On the minimum hardware the shadow pass should stay under 1.5 ms (`--benchmark` reports it as `shadow`).

**Skeletal animation**: a model with an armature (exported from Blender with its actions, {doc}`blender`) is a skinned model: up to 64 bones, four bones per vertex, and every action becomes a clip baked at 30 frames per second. MkRender's inspector **Clip** box lists the clips; choosing one stores it in the object's `anim` field and MkRender, the editor and the game loop it (the field is view-only and not part of the content hash; `anim run 0.2` starts 0.2 s into the clip). Game view code picks clips through the animation state table (below), or plays them itself: `asset::samplePose` for a time, `asset::blendPoses` for cross-fades, `asset::skinPalette`, then `DrawList::addSkinned`. Animation is only drawn: hit boxes and game rules use the simulation's shapes. Code under `sim/` that needs a pose (for example an active ragdoll's target) uses `asset::samplePoseTick`, which gives the same bits on every machine. `scenes/anim.scene` shows the sample figure `models/characters/rig_figure.glb` in its rest pose and three clips.

**Animation states**: `assets/tables/animation.table` (the **Tables** panel) says which clip a character plays and when to switch, so idle/run/jump/attack switching is data instead of code. Each row is one state; its id is `<set>.<state>`, where the set is a character kind (`pawn.idle`), and the first row of a set is where it starts. **Clip** is one clip, or a 1D blend `idle 0 walk 1.5 run 4` blended by the **Blend parameter** (for example `speed`). **Transitions** are checked in order and the first one that holds wins: `move if speed > 0.6 and grounded; attack on attack; idle if end` (compare a parameter with `> < >= <= == !=`, `grounded` / `!grounded` for on and off, `end` when a non-looping clip has finished, `on <trigger>` for one-off triggers). **Blend time** cross-fades into the state. **Events** are pairs of a point in the clip's cycle (0 to below 1) and a feedback table row, such as `0.25 Footstep 0.75 Footstep`: the row's sound and effect play at the character. Game view code sets the parameters every frame and calls `asset::updateAnim` and `asset::animPose` (`AnimParams::set("speed", ...)`, `AnimParams::trigger("attack")`); the sandbox pawns use the `pawn` set with `speed`, `grounded` and a `push` trigger. Changes to the file apply while the game runs. Like clips, states are only drawn and never change the game's rules.

**Material features** are set per material in Blender's MealKit material panel ({doc}`blender`): outline, wind sway, rim light and dissolve. A model can mix materials with and without features. **View > View Mode > Material Features** in the editor shows which material uses which feature.

**Per-object values** change while the game runs: a white flash (for example when a character is hit) and the dissolve progress. The game's view code sets them on the object it draws ({doc}`game_code`).

`scenes/styles.scene` in the engine folder shows all of it; the graphics tests draw it with each lighting model.

**Post processing and color grading**: the scene is drawn in HDR and one full-screen pass turns it into the picture: AgX tone mapping (the same family as Blender's default view, so colors match what you saw in Blender), exposure, bloom around light brighter than **Bloom threshold**, a color LUT, vignette, film grain, chromatic aberration and FXAA anti-aliasing. The values belong to the scene: the **Post-processing** section of MkRender's **Environment** window edits them and the scene file keeps them as `post` lines (view-only, not part of the content hash). To grade colors, press **Grading capture**: MkRender saves the view without a LUT to `art/grading/<scene>.png` with a neutral `neutral.cube`. Grade the picture in DaVinci Resolve, Photoshop or another tool, export a 3D `.cube` LUT (32 points is best; other sizes are resampled) into `assets/lut/`, and pick it under **Color LUT**; a changed file is picked up again while the editor is open. Players can turn bloom, film grain, chromatic aberration and anti-aliasing off in the settings, and the color-blind modes are folded into the same LUT. The pass should stay under 1 ms on the minimum hardware (`--benchmark` reports it as `post`). `scenes/post.scene` uses every effect with the sample LUT `lut/warm.cube`.

## Cameras and cutscenes

**Virtual cameras**: add a **Virtual camera** object (**Add** in MkRender) for each way the game can be seen. The camera brain shows the active camera with the highest **Priority** and blends to a new one over its **Blend time** (`EaseInOut`, `Linear` or `Cut`). **Body kind** decides where it stands: `ThirdPerson` is a spring arm behind the target that the player turns and that pulls in when a wall is in between, `FirstPerson` sits at the target's eyes, `TopDown` looks down at a fixed angle, `Orbit` circles the target (or its own position) at **Orbit speed**, `Rail` moves along the objects named in **Rail path** to the point closest to the target, `Fixed` stays where it is placed, and `Free` is a spectator camera. **Follow target** and **Look-at target** are object names; an empty follow target means the Pawn the player possesses. **Dead zone** and **Follow damping** keep the camera calm while the target moves a little. A **Field of view** of 0 uses the player's setting. Without any active camera the game's own default camera is used (the sandbox: a third-person camera from `view.tuning`).

Game code never moves the camera itself. Game view code keeps one `camera::Brain`, gives it the player's look and zoom input, the possessed Pawn's position, the feedback table's shake and a wall ray every frame (`BrainInput`), and only switches cameras with `setActive(name, on)` and `setPriority(name, value)`. The sandbox turns on the arena's `results` camera when the match reaches its results.

**Cutscenes** are camera animations made in Blender: animate a camera and export it as glTF into `assets/models/` (for example `models/cutscenes/intro.glb`). MealKit only plays them back; there is no timeline editor. Each row of `assets/tables/cutscenes.table` (the **Tables** panel) is one cutscene: **File**, the **Animation name** (empty for the first), **Blend from/back to the game camera** times, whether player input is blocked, and **Events**, pairs of a time in seconds and a feedback table row (`0 CutsceneStart 2.5 Whoosh`). Game view code calls `Brain::playCutscene(cutscenes, "intro")`. In multiplayer, start a shared cutscene from something the simulation decides (a tick event or a match phase), so every player sees it on the same tick; the simulation keeps running and only input is held back. The sandbox plays `intro` during the countdown. Solo staging, like a camera on your own death, can start at once on the view side.

**Previewing in the editor**: select a virtual camera in MkRender and choose **Editor > Look through selected camera** to see the editor's viewport through it (in edit mode there is no Pawn to follow, so a follow camera stands where it is placed). **View > Preview Cutscene** plays a row of the cutscene table in the viewport, with its event sounds, and returns to the editor camera at the end. Esc, or looking around with the right mouse button, stops either preview.

## Asset budget

Each model has a budget so that it stays light enough for the minimum spec (integrated graphics). The kind of model is the **first folder under `assets/models/`**:

| Folder | Kind | Triangles | Texture size | Bones | Materials |
|---|---|---|---|---|---|
| `characters/` | Character | 15,000 | 2048 px | 64 | 4 |
| `environment/` | Background | 20,000 | 2048 px | 0 | 4 |
| `props/` or anywhere else | Prop | 3,000 | 1024 px | 0 | 2 |

- The limits are project settings (**Project > Settings**, `budgetCharactersTriangles`, `budgetPropsMaterials`, ...). The defaults above are a first guess and will be corrected with benchmarks on the minimum spec.
- A model over its budget still loads. The log says `Model models/ring.glb is over the props budget: 3072 triangles (budget 3000)`, and the **Over Budget** view mode shows it in red. The example ring is a little over on purpose.
- Triangles are counted on the most detailed LOD and texture size is the longest side of the largest texture. Bones are counted once the engine reads skeletons.
- The Blender add-on checks the same limits before exporting ({doc}`blender`).

## Changing assets while the editor is open

The editor reloads changed files by itself, so an artist can export from Blender and look at the result without restarting:

- **Models**: every half second the editor checks the model files the scene uses. A changed (or newly created) file is loaded again and every object using it shows the new model. The status bar says `Reloaded model: models/tree.glb`. If the new file cannot be loaded, the log says why and the old model stays.
- **Scene**: if the open scene file is changed outside the editor (for example by a merge or another tool) and you have no unsaved changes, the editor opens it again and keeps the selection. With unsaved changes it only warns; saving then writes over the file on disk.
- **During play** nothing is reloaded, because a model's collision hull is simulation data that every player must share. Files changed during play are picked up when you stop. The changed model then also changes the content hash, so it takes effect for multiplayer from the next play.

## Where numbers go

Numbers are not constants in code. Each kind of number has one place, chosen by what it affects (the engine's {engine}`coding model <docs/CODING_MODEL.md>`, "Where do numbers go"):

| Kind of value | Place | Edited in |
|---|---|---|
| Game rules (speed, mass, chance, cooldown) | `MEALKIT_STRUCT(Tuning)` → `assets/game.tuning`, read as `world.tuning` | Tuning panel, Game tab |
| Values that differ per map (areas, counts, heights) | Scene objects; ranges and heights are the position and size of an **area object** | Viewport and inspector |
| Many rows of the same shape (weapons, items, enemy kinds) | Definition table `assets/tables/*.table` | Tables panel, or a spreadsheet through CSV |
| Values that are only seen (camera, colors, effects) | `MEALKIT_STRUCT(ViewTuning)` → `assets/view.tuning`, read as `ctx.viewTuning<ViewTuning>()` | Tuning panel, Display tab |
| Whole-project settings | `mealkit.project` | Project > Settings |

Code keeps only unit conversions, algorithm constants and trivial values such as 0 and 1. SimCheck warns about other float literals in `sim/` (`SIM012`); an algorithm constant is marked with `// const-ok: <reason>` at the end of the line.

### Time values

Time values (cooldowns, respawn delays) are declared with the `Ticks` type: `MEALKIT_FIELD(Ticks, respawn, Ticks::seconds(1.5f), "...")`.
Files and the editor show seconds; on load the value is rounded once to whole ticks, and `sim/` code uses ticks only (`TickTimer::start(tick, world.tuning.respawn)`).

### View tuning

View tuning is not part of the content hash, so it can differ between players and changes apply at once, even during multiplayer play: the engine reloads `assets/view.tuning` when the file changes.
Colors use the `Color` field type (`#RRGGBB` in files, a color picker in the editor). `sim/` code cannot include `view/` headers, so the simulation never reads view tuning.

### Area objects

A scene object kind declared with `kObjectFlags = mealkit::reflect::kObjectArea` is an invisible box. The editor draws only its edges, and you pick it by clicking an edge. The game does not draw it; it reads the box with `scene::areaBounds()`.
In the example, the match area's floor is the fall height and its top is where fallen boxes are dropped again, and box spawn areas hold the number and kind of boxes to scatter.

### Definition tables

A table has a row type declared with `MEALKIT_STRUCT` and is registered with `MEALKIT_TABLE(Row, "tables/props.table", 0)`. The file has a `row <id>` line followed by that row's values.
Other data points at a row with a `RowRef<Row>` field (the row id in files, a dropdown in the editor). The game reads tables with `data::loadTable` when a match starts, and simulation code reads rows by number.
In the Tables panel (Window > Data, `Ctrl+T`) you add, copy, delete and reorder rows, edit cells, and see every reference to a missing row id. **CSV import and export** let you balance a table in Google Sheets or Excel: the first column is `id` and the other columns are the field paths. Importing replaces the table.
A table registered with `reflect::kTableView` is display-only and stays out of the content hash.

### Rule rows

With the `objects` source module, designers build map gimmicks from table rows instead of new code. Programmers declare the list of effects (such as a speed multiplier) and a row type with four fields: when (`Enter`, `Inside`, `Exit`, `Timer`), effect, amount and duration. Each row goes in `tables/rules.table`, and a rule zone (an area) or a rule timer placed in the scene picks a row, for example "inside the mud: speed ×0.6". A duration of 0 means the effect lasts while the player is inside, or while the timer is on. The rows are table data in the content hash, so every peer runs them the same way. The module's docs ("Rule rows") show the code to add.

## Game text and languages

Text that players see is never written in code. Each language has a string table `assets/strings/<language>.txt` with one `key = text` per line:

```text
# assets/strings/ko.txt
menu.start = 시작
hud.score = 점수 <1>{score}</1>점
```

The view side uses only keys: `ctx.strings.get("menu.start")`, or `ctx.strings.format("hud.score", {{"score", "12"}})` to fill the `{name}` places.
`\n` is a line break. Numbered tags such as `<1>...</1>` mark text spans with their own style; the game UI reads them, and translators only move them.

- The default language is `language` in the project settings (`ko`). The game picks another with `--lang en` (later, the settings screen).
- A key missing in the chosen language comes from the default language; a key missing everywhere shows the key name and logs one warning.
- The tables are reloaded when they change.
- **Every character must be in a font.** Before the game builds, `mealkit_stringcheck` checks that each character of the tables is in one of the fonts in `assets/fonts` (`.ttf`, `.otf`, `.ttc`). A missing one stops the build with `error STR001` and the line. Put a font's license next to it as a `.txt` file; the release build adds it to the notices.

The example uses Pretendard (SIL Open Font License) for Korean and English.

## Content hash

When the scene's collision data, model files, tuning values or simulation tables change, the content hash changes. Peers using different data are refused when they connect. View tuning and display-only tables are not included.
