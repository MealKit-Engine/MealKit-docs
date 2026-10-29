# Asset

This page explains how 3D models are loaded: reading glTF files, optimizing meshes, making levels of detail, and the data that physics and the content hash take from a model.
How to add models to a project is in {doc}`../../manual/assets`. The code is in {engine}`engine/src/mealkit/asset`.

`asset` comes after `render` and before `online` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"). It reads scenes (`scene`) and uploads meshes through the renderer (`render`).
Headless builds (servers, tests) also load models, for collision and hashing, without a renderer.

## The model cache

`asset::ModelCache` ({engine}`engine/src/mealkit/asset/ModelCache.h`) loads a model the first time its path is asked for and keeps it until the cache is destroyed.
Models are stored by the path written in the scene (relative to `assets/`). A path that failed to load is stored as failed, so it is not tried again every frame.

A loaded `asset::Model` has:

- up to 3 mesh ids (`lods`) and the triangle count of each level,
- the bounding box in model space,
- the hull points for physics,
- the hash of the file contents.

`setRenderer` stores a plain function pointer that calls `Renderer::createMesh`. This call sits in an inline function in the header, so a headless program that never calls `setRenderer` links without the renderer at all. Without a renderer, the cache still builds bounds, hull points and hashes.

`resolve` uses a path as it is when that file exists, otherwise it looks for `assets/<path>` with `findAsset`. `boxMesh` gives the unit box that entities without a model use.

## Reading glTF

`loadGltf` ({engine}`engine/src/mealkit/asset/ModelCache.cpp`) uses cgltf for `.glb` and `.gltf` files:

1. cgltf parses the file, loads its buffers and validates it. File reading is replaced with the engine's `openFile`, so paths with Korean folder names (UTF-8) work.
2. The file hash is computed from the binary chunk, every buffer and the JSON text.
3. The nodes of the default scene (or the first scene, or all root nodes) are walked recursively. Each mesh node's world matrix comes from `cgltf_node_transform_world`, so the whole model becomes one mesh in model space.
4. For every triangle primitive it reads positions, normals, the first UV set and the first vertex color (stored as sRGB RGBA8; the alpha is the wind amount). Each vertex keeps the number of its primitive's material.
5. glTF is right-handed and MealKit is left-handed (y up), so z is negated for positions and normals and the triangle winding is reversed. When the node matrix mirrors (negative determinant), the winding is reversed once more.
6. If any primitive had no normals, smooth normals are computed for the whole mesh: each triangle adds its unnormalized face normal (the cross product, whose length is twice the area) to its three vertices, and the sums are normalized.

Each glTF material becomes a renderer material (base color, metallic-roughness, normal and emissive values and textures, alpha clip; see {doc}`render`). Its `extras` (Blender custom properties) are read by `asset::applyMaterialExtras`: a small reader takes the top-level keys and keeps numbers and number arrays. Keys that start with `mealkit_` turn on the style preset features: `outline`, `wind`, `rim` and `dissolve` (a number) turn a feature on and set its main value, and `outlineColor`, `rimColor` and `dissolveColor` (three numbers, linear color) only change a color. An unknown `mealkit_` key or a value of the wrong kind gives a warning with the model and material name and is ignored; other keys are not looked at.
The same list is written into the add-on's `schema.json` (`materialFeatures`, with labels and the engine's default values), so the Blender panel offers exactly what the loader reads.

Skins and animation are not read yet.

## Hull points and bounds

Before any optimization, the loader takes the bounding box and the hull points **from the original vertices**: every `stride`-th vertex, where `stride` is the vertex count divided by 1024 (at least 1).
The game's simulation builds a convex physics shape from these points (the sandbox sample does this in `sim/World.cpp`), and the simulation must be the same on every peer. Taking them from the file data, not from meshoptimizer's output, means they never depend on how a library version reorders vertices.

## Optimizing

`optimize` runs four meshoptimizer passes on the full mesh:

1. `meshopt_generateVertexRemap` finds identical vertices and builds one shared vertex buffer.
2. `meshopt_optimizeVertexCache` reorders triangles so that recently used vertices are reused, which cuts vertex shader work.
3. `meshopt_optimizeOverdraw` reorders triangle groups so that front surfaces tend to draw first, with a threshold of 1.05 (it may make the vertex cache at most 5 % worse).
4. `meshopt_optimizeVertexFetch` reorders vertices in the order triangles use them, so memory is read in sequence.

## Levels of detail

`makeLod` simplifies with `meshopt_simplify`, which collapses edges while keeping the error under a limit:

| Level | Made from | Target triangles | Error limit |
|---|---|---|---|
| LOD 0 | the file | all | - |
| LOD 1 | LOD 0 | 50 % | 0.02 |
| LOD 2 | LOD 1 | 40 % of LOD 1 | 0.05 |

A level is kept only when it has at most 80 % of the indices of the level it came from. A simple model that cannot be reduced enough has only LOD 0, and the log says "too simple to reduce".
Each level gets its own vertex cache and vertex fetch optimization.

`pickLod` chooses a level per instance from its size on screen: half the bounding box diagonal times the largest absolute scale, divided by the distance to the camera.
Above 0.08 it uses LOD 0, above 0.03 LOD 1, and below that LOD 2 (or the last level the model has). The choice is only for drawing; the simulation never sees it.

## File hash

`hashModels(scene)` combines the file hash of every model a scene uses, except decorations, in entity order (0 for a model that failed to load).
The game adds it to the scene's content hash (see {doc}`scene`), so a peer whose model files differ is refused before a match.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Load-once cache | `ModelCache::get` | Keeps models by path in a hash map. Failures are cached too, so a missing file is reported once. |
| Optional dependency through a function pointer | `ModelCache::setRenderer` | The only renderer call is in an inline header function, so headless builds link without the renderer. |
| Scene graph flattening | `visitNode` | Applies each node's world matrix to its vertices, so a model is one mesh in model space. |
| Handedness conversion | `appendPrimitive` | Negates z and reverses winding, with a determinant check for mirrored nodes. |
| Area-weighted smooth normals | `computeNormals` | Adds raw cross products of each triangle to its vertices and normalizes, so bigger triangles count more. |
| Deterministic sampling for physics | `loadGltf` | Hull points are every n-th original vertex, independent of the optimizer, so every peer builds the same hull. |
| Vertex deduplication | `meshopt_generateVertexRemap` | Merges identical vertices into one indexed buffer. |
| Vertex cache optimization | `meshopt_optimizeVertexCache` | Orders triangles for GPU vertex reuse. |
| Overdraw optimization | `meshopt_optimizeOverdraw` | Orders triangle groups so fewer hidden pixels are shaded. |
| Vertex fetch optimization | `meshopt_optimizeVertexFetch` | Orders vertices by first use for sequential memory reads. |
| Mesh simplification by edge collapse | `meshopt_simplify` in `makeLod` | Builds lower levels of detail under an error limit, and keeps a level only when it saves at least 20 %. |
| Screen-size LOD selection | `ModelCache::pickLod` | Bounding radius over distance approximates the share of the screen a model covers. |
| Content hashing (FNV-1a) | `Hasher` in `loadGltf`, `hashModels` | Hashes the file bytes so peers can compare models before a match. |
