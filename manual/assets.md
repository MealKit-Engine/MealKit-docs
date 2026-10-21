# Assets

## 3D models (glTF)

- Put `.glb` (recommended) or `.gltf` files under `assets/models/`. In Blender: File → Export → glTF 2.0, format glTF Binary.
- Scenes store model paths **relative to `assets/`**, like `models/tree.glb`.
- On load, meshoptimizer optimizes the vertex cache, overdraw and fetch order, and builds **two more LOD levels** for models with many triangles. Distant objects use the lighter LODs automatically.
- Colors come from the material base color (baseColorFactor) and vertex colors. **Textures are not supported yet.**
- A solid box with a model collides as the **convex hull of the model's vertices** (concave parts are filled in). Hull points are taken from the original vertices before optimization, so they are the same on every PC.
- The sample models (tree, rock, ring) can be regenerated with `python tools/make_sample_models.py`.

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
| Values that differ per map (areas, counts, heights) | Scene objects; ranges and heights are the position and size of an **area object** | Scene view and inspector |
| Many rows of the same shape (weapons, items, enemy kinds) | Definition table `assets/tables/*.table` | Tables panel, or a spreadsheet through CSV |
| Values that are only seen (camera, colors, effects) | `MEALKIT_STRUCT(ViewTuning)` → `assets/view.tuning`, read as `ctx.viewTuning<ViewTuning>()` | Tuning panel, Display tab |
| Whole-project settings | `mealkit.project` | File > Project Settings |

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
In the Tables panel (View > Tables, `Ctrl+T`) you add, copy, delete and reorder rows, edit cells, and see every reference to a missing row id. **CSV import and export** let you balance a table in Google Sheets or Excel: the first column is `id` and the other columns are the field paths. Importing replaces the table.
A table registered with `reflect::kTableView` is display-only and stays out of the content hash.

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
