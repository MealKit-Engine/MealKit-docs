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
| Name | The path under `assets/models/` without `.glb`, such as `props/crate`. The first folder sets the budget kind ({doc}`assets`). Empty means the `.blend` name (a prop). |
| Selected only | Export only the selected objects; otherwise every visible object. |

The panel shows the budget of the model's kind, read from `mealkit.project`. **Check** lists what the engine will not show the way Blender does, and triangle or material counts over the budget. **Export to MealKit** runs the same check and, if there is no error, writes `assets/models/<name>.glb`. With the editor open, the model changes in the scene right away ({doc}`assets`).

All exported objects become **one model**: the engine merges the meshes and bakes their transforms.

## What the engine reads

| Supported | Not yet |
|---|---|
| Triangles (faces are triangulated on export), normals, the first UV map | A second UV map |
| Principled BSDF: Base Color, Metallic, Roughness, Normal (through a Normal Map node) and Emission, as values or image textures | Base color from other nodes, other BSDF inputs |
| Alpha clip | Alpha blend |
| The active color attribute (multiplied with the base color) | Shape keys, a second armature |
| One armature with up to 64 bones, and its actions (each action becomes a clip) | Animated objects without an armature |

The check warns about the parts in the right column. They are exported without them (an armature with more than 64 bones is drawn in its bind pose).
The list comes from the engine itself: the add-on's `schema.json` is checked against the engine's model loader by the engine's unit tests, so the add-on and the engine cannot disagree.

## Material panel

**Properties > Material > MealKit** shows the engine's material features. **Add** saves a feature as a custom property of the material (`mealkit_<name>`), which goes into the glTF file as `extras`; the **X** removes it. You set the look here instead of writing shaders ({doc}`assets`).

| Feature | Value | Notes |
|---|---|---|
| Outline | width in metres (default 0.02), and a color | A line of the outline color around the object. Use smooth normals: hard edges leave gaps in the line. |
| Wind | sway in metres (default 0.1) | Paint the amount into the **alpha of the color attribute**: 0 at the root, 1 at the tip. Without alpha the whole object sways. |
| Rim light | strength (default 0.5), and a color | The edges facing away from the camera get brighter. |
| Dissolve | edge width (default 0.05), and a glow color | The object disappears in a noisy pattern as the game raises its dissolve value; the edge glows. Without the game setting the value, nothing happens. |

The color of a feature appears after its main value is added. Colors are linear; values above 1 make the glow brighter. The engine warns when it finds a `mealkit_` property it does not know.
