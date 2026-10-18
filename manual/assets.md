# Assets

## 3D models (glTF)

- Put `.glb` (recommended) or `.gltf` files under `assets/models/`. In Blender: File → Export → glTF 2.0, format glTF Binary.
- Scenes store model paths **relative to `assets/`**, like `models/tree.glb`.
- On load, meshoptimizer optimizes the vertex cache, overdraw and fetch order, and builds **two more LOD levels** for models with many triangles. Distant objects use the lighter LODs automatically.
- Colors come from the material base color (baseColorFactor) and vertex colors. **Textures are not supported yet.**
- A solid box with a model collides as the **convex hull of the model's vertices** (concave parts are filled in). Hull points are taken from the original vertices before optimization, so they are the same on every PC.
- The sample models (tree, rock, ring) can be regenerated with `python tools/make_sample_models.py`.

## Tuning values

Numbers the simulation uses (movement speed, jump strength, and so on) are not constants in code. The game declares them in `MEALKIT_STRUCT(Tuning)` and their values live in `assets/game.tuning`.
The simulation reads them through `world.tuning`, and the editor's Tuning panel edits them. Where each kind of number belongs is in the engine's {engine}`coding model <docs/CODING_MODEL.md>` ("Where do numbers go").

## Content hash

When the scene's collision data, model files or tuning values change, the content hash changes. Peers using different data are refused when they connect.
