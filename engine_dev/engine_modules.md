# Engine modules

The engine is a small kernel plus engine modules. The kernel (`engine/core/`) holds memory, logging, math, reflection, the service registry and the platform layer. Everything else (the renderer, physics, networking, the editor) is an engine module in `modules/<name>/`, and each module has its own repository under `MealKit-Engine`. The design and its reasons are in {engine}`docs/ENGINE_MODULES.md`.

Engine modules are compiled in and chosen when the game is built. They are not plugins loaded at run time, so the shipped game is still one file.

## A module

Each module folder has a `module.txt`, the same file as a source module's, with `type engine`:

```text
@format module 1
type engine
name render
version 0.1.2
engine 0.9
kind view
layer framework
requires rhi 0.1 scene 0.1
summary Renderer
```

- `kind` is `sim` (code the simulation runs, under the determinism rules), `view` (window, drawing, sound, input) or `tool` (editor and debug tools).
- `layer` is `platform`, `kernel`, `core`, `framework` or `app`, from low to high. A module includes only its own layer and the layers below.
- `requires` lists the modules this one may include. `optional` lists modules it can work without; their code sits inside `#if MEALKIT_HAS_<NAME>`.
- `tools\check_modules.ps1` checks the manifests and every include against them.

Headers other code may include are in `include/mealkit/<name>/`, the rest in `src/mealkit/<name>/`, and the module's editor panels in `editor/`.

## Choosing modules

Engine modules are added, updated and removed like source modules ({doc}`../manual/modules`): they are folders in the game's `modules/`, and the game is built with the ones that are there. New projects start with every module of the `standard` preset.

```text
tools\module.ps1 remove audio -Project <folder>         # a game without sound
tools\module.ps1 add audio -Project <folder>            # back in, at the engine's version
tools\module.ps1 add camera@0.1.2 -Project <folder>     # one module at another version
tools\module.ps1 update render -Project <folder>        # to the engine's version after an engine update
tools\module.ps1 add -Preset solo -Project <folder>     # every module of a preset
tools\module.ps1 list -Project <folder>
```

- `update` keeps files you changed and writes the new version next to them as `<file>.new`, as for source modules. Engine updates don't change the copies until you update them.
- `remove` refuses while another module requires it, or while game code includes it outside `#if MEALKIT_HAS_<NAME>`.
- Modules that need a missing module go with it: without `net` there is no `online` either. If the game framework itself needs it, the build stops and names the module to add.
- A project is built with exactly the engine modules in its `modules/`. With none there it has only the kernel, and game code that includes a missing module stops the build with the module names and the lines. Only the engine's own samples use every module of the engine.
- The editor always has every module at the engine's version.

| Preset | What it has |
|---|---|
| `standard` | every module (what new projects get) |
| `solo` | everything except `net` and `online`: single-player games. Hosting and joining report that the build has no multiplayer |

The build configuration `Presets` builds the samples with `solo` and without `audio`, as CI does. Other combinations and versions are the game's own responsibility; peers with different simulation modules can't join each other.

## Vendored copies and the lock file

The engine repository keeps a copy of every module in `modules/`, so cloning `MealKit` alone is enough to build. `modules.lock` records the repository, tag and commit each copy comes from. An engine version means `VERSION` plus `modules.lock`.

`tools\module.ps1 engine` keeps the engine's copies in step (games use the other `tools\module.ps1` commands):

| Command | What it does |
|---|---|
| `engine status` | compares each copy with its locked commit |
| `engine sync [name]` | rewrites copies from the locked commits |
| `engine bump <name> [tag]` | locks a new tag of a module repo and copies it in |
| `engine local on [name]` | links `modules/<name>` to the checkout beside the engine (`..\module-<name>`), for a change that spans repos; `engine local off` puts the copy back |

A change to a module goes into its own repository first: commit, tag, then `bump` in the engine, so the engine gets the new copy and the lock in one commit. Each module repository runs the shared workflow `engine-module.yml`, which builds the engine with that repository in place of its copy.
