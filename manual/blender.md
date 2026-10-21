# Blender add-on

The MealKit add-on checks a Blender scene against what the engine can read and exports it into the project with the right settings in one click. It lives in the engine repository, in {engine}`tools/blender-addon/mealkit`.

The add-on follows one Blender version: **Blender 5.2 LTS** (supported until July 2028). Other versions may work but are not tested.

## Installing

1. Build the extension file once:

   ```bat
   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension build --source-dir D:\MealKit\tools\blender-addon\mealkit --output-dir D:\MealKit\build
   ```

2. In Blender: **Edit > Preferences > Get Extensions**, the menu at the top right, **Install from Disk**, and pick `build\mealkit-0.1.0.zip`.

When the engine is updated, build and install the file again.

## Exporting a model

Keep the `.blend` files inside the project, usually in `art/` (sources are not shipped). Then open the **MealKit** tab in the 3D view sidebar (`N`):

| Field | Meaning |
|---|---|
| Project | Found by walking up from the `.blend` file to the folder with `mealkit.project`. Set it by hand to export somewhere else. |
| Name | The file name under `assets/models/`. Empty means the `.blend` name. |
| Selected only | Export only the selected objects; otherwise every visible object. |

**Check** lists what the engine will not show the way Blender does. **Export to MealKit** runs the same check and, if there is no error, writes `assets/models/<name>.glb`. With the editor open, the model changes in the scene right away ({doc}`assets`).

All exported objects become **one model**: the engine merges the meshes and bakes their transforms.

## What the engine reads

| Supported | Not yet |
|---|---|
| Triangles (faces are triangulated on export), normals | Image textures and UV coordinates |
| Material base color (the Principled BSDF value) | Base color from other nodes |
| The active color attribute (multiplied with the base color) | Armatures, animation, shape keys |

The check warns about the parts in the right column. They are exported without them (a textured material shows its base color value, an armature exports the current pose).
The list comes from the engine itself: the add-on's `schema.json` is checked against the engine's model loader by the engine's unit tests, so the add-on and the engine cannot disagree.

## Material panel

**Properties > Material > MealKit** will show the engine's material features (such as outlines) as fields saved in the glTF file. There are none yet; the panel says so.
