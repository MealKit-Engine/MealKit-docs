# Scene

This page explains how a scene is stored and read: the `.scene` text format, how parent and child transforms combine, and how the game turns the tree into a flat list.
How to edit scenes is in {doc}`../../manual/editor`. The code is in {engine}`engine/src/mealkit/scene`.

`scene` comes after `loc` and before `render` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존"). It uses only `core` (math, reflection, hashing) and `platform` (files).
It knows nothing about drawing: an entity's model is only a path, and `asset` loads it later.

## What a scene holds

A `scene::Scene` ({engine}`engine/src/mealkit/scene/Scene.h`) is:

- `entities`: a list of `Entity` values. Each has an `id`, a `parent` id (0 = top level), a `name`, a kind name (`type`), a position, a rotation (quaternion), a scale, a color, render flags, an optional glTF `model` path and the text of its game fields.
- `environment`: sun direction and color, sky and ground colors for the ambient light, fog color and fog density. The renderer reads these values (see {doc}`render`).
- `nextId`: the id the next new entity gets.

There are three built-in kinds: `solid` (drawn and collides), `decoration` (drawn only, `kObjectCosmetic`) and `spawn` (a player start, `kObjectMarker`, not drawn in the game).
Every other kind comes from the game's `MEALKIT_OBJECT` declarations.

Game fields are stored as text by field path (`reflect::TextFields`), not as C++ values. So a scene still loads when the game DLL is missing or a field was renamed, and the values stay in the file.
The game reads one entity with `scene::readObject<T>(entity)`, which fills a `T` from the text with `reflect::fromText`. A field that the file does not have keeps the default from its declaration.

## The .scene format

`scene::save` ({engine}`engine/src/mealkit/scene/Scene.cpp`) writes plain text, one value per line:

```text
# MealKit scene
@format scene 3

sun 0.400000006 0.800000012 0.300000012
sunColor 1 0.949999988 0.850000024
sky 0.300000012 0.379999995 0.5
groundColor 0.200000003 0.170000002 0.140000001
fog 0.5 0.620000005 0.779999971 0.00800000038
hdri textures/hdri/kloofendal_partly_cloudy_1k.hdr
hdriIntensity 1
hdriRotation 0

entity
id 1
name Ground
kind solid
position 0 -0.5 0
rotation 0 0 0 1
scale 120 1 120
color FF609676
flags 1
end
```

- Numbers are written with `%.9g`. Nine significant digits are enough to write any 32-bit float and read back exactly the same bits, so saving and loading never changes a value. This matters because the scene's collision data is part of the content hash that peers compare.
- The `hdri` lines are written only when the scene has a sky HDRI (format 3; files of format 1 and 2 are read the same way). They are view-only and not part of the content hash.
- `parent` is written only when it is not 0, and `model` only when it is set. `color` is eight hex digits (RGBA8). Each game field is one `field <path> <value>` line.

`scene::load` reads the file line by line. The first word is the key and the rest of the line is the value:

- `version` must be 1 or 2. A kind name must look like a C++ type name (a letter, then letters, digits or `_`).
- An unknown key writes a warning and is skipped, so an older engine can open a newer file that only added keys.
- A value that cannot be read stops the load with `line N: invalid '<key>'`. A file that ends inside an entity fails with `missing 'end'`.

After reading, the loader repairs what a hand edit could break:

- Entities with id 0 get new ids above the largest id, and `nextId` becomes the largest id plus one.
- A parent that does not exist, or a parent chain that loops back, is reset to the top level with a warning.

## Hierarchy

Parent and child exist only for editing. Each entity's position, rotation and scale are relative to its parent.

`worldTransform` walks up the parent chain and combines the transforms one by one (`combine` in `Scene.cpp`):

- The child's position is multiplied by the parent scale per axis, rotated by the parent rotation and added to the parent position.
- The rotations are multiplied and normalized.
- The scales are multiplied **per axis**. When a rotated parent has a non-uniform scale, a real matrix would shear the child; this is dropped on purpose, so every transform stays position, rotation and scale.

The walk stops after as many steps as there are entities, so a broken chain cannot loop forever.

`setWorldTransform` does the reverse when the editor moves an entity: it takes the parent's world transform, rotates the world position by the inverse rotation (the conjugate quaternion) and divides by the parent scale. A scale near zero is not divided (`safeDiv`), so a flattened parent does not create infinite values.

`isDescendant` and `subtree` answer "is this entity under that one" and "this entity and all its children". The editor uses them for reparenting and for deleting or copying a branch.

## flattened()

At match start the game does not use the tree. `scene::flattened(scene)` returns a copy where every entity has its world transform and `parent = 0`, in the same order as before.

The simulation then works on a flat array: no parent lookups per tick, and the order is the file order on every peer. This keeps the simulation fast and deterministic.

## Content hash

`Scene::contentHash` hashes the data that can change the result of a match. Peers compare it before a match starts.
It skips entities whose kind is cosmetic (`kObjectCosmetic`) and game fields declared as view-only (`kFieldView`), and it never includes the color.
For the rest it hashes the id, parent, kind, transform, model path and field text. The model files themselves are hashed by `asset` (see {doc}`asset`).

## Other helpers

- `visibleInGame` is false for marker and area kinds (`kObjectMarker`, `kObjectArea`); the editor still draws them.
- `areaBounds` turns an area entity of a flattened scene into an axis-aligned box. The rotation is ignored.
- `makeDefault` builds the default arena: ground, four walls, a ramp, a platform, pillars, a block, a crate, a banner and four spawn points. Its rotations are written as quaternion constants instead of being computed with sine and cosine, so the scene is the same bits on every PC.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Line-based text format | `scene::save` / `load` | One key and value per line, so files are readable, merge well in version control and can be fixed by hand. |
| Round-trip float formatting | `%.9g` in `save` | Nine significant digits always read back to the same 32-bit float, so save and load never change a value or a hash. |
| Tolerant reading | `load` | Unknown keys are warned about and skipped. Bad parents and missing ids are repaired after reading. |
| Fields kept as text | `Entity::fields` | Values are stored by field path, so data survives a missing or changed game DLL. |
| Transform composition without matrices | `combine` | Position, rotation and scale are combined as separate parts. Non-uniform scale under rotation does not shear. |
| Inverse transform | `setWorldTransform` | Uses the conjugate quaternion as the inverse rotation and a guarded division for scale. |
| Bounded parent walks | `worldTransform`, `isDescendant`, `load` | Every walk up the chain stops after as many steps as there are entities, so a cycle cannot hang. |
| Flattening the hierarchy | `flattened` | The game gets a flat array in world space at match start, so the simulation never resolves parents. |
| Content hashing (FNV-1a) | `Scene::contentHash` with `Hasher` | Hashes only data that affects the match, so changing a color or a decoration does not block peers. |
| Constant rotations | `makeDefault` | Quaternions are literal values, so no trigonometry result can differ between machines. |
