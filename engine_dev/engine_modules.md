# Engine modules

The engine is a small kernel plus engine modules. The kernel (`engine/core/`) holds memory, logging, math, reflection, the service registry and the platform layer. Everything else (the renderer, physics, networking, the editor) is an engine module in `modules/<name>/`, and each module has its own repository under `MealKit-Engine`. The design and its reasons are in {engine}`docs/ENGINE_MODULES.md`.

Engine modules are compiled in and chosen when the game is built. They are not plugins loaded at run time, so the shipped game is still one file.

## A module

Each module folder has a manifest, `engine-module.txt`:

```text
@format engine-module 1
name render
version 0.1.0
kernel 0.9
kind view
requires rhi 0.1 asset 0.1
summary Renderer
```

- `kind` is `sim` (code the simulation runs, under the determinism rules), `view` (window, drawing, sound, input) or `tool` (editor and debug tools).
- `layer` is `platform`, `kernel`, `core`, `framework` or `app`, from low to high. A module includes only its own layer and the layers below.
- `requires` lists the modules this one may include. `optional` lists modules it can work without; their code sits inside `#if MEALKIT_HAS_<NAME>`.
- `tools\check_modules.ps1` checks the manifests and every include against them.

Headers other code may include are in `include/mealkit/<name>/`, the rest in `src/mealkit/<name>/`, and the module's editor panels in `editor/`.

## Choosing modules

A game picks its modules in `mealkit.project`, any combination:

```text
enginePreset standard              # starting point
engineModules camera               # added
engineWithout net                  # taken out
engineModuleVersion render v0.2.0  # this module at another version
```

Modules that need a left-out module go with it: leaving out `net` also leaves out `online`. If the game framework itself needs it, the build stops and names the module. Changing these lines rebuilds the game. The editor always has every module at the engine's version.

| Preset | What it has |
|---|---|
| `standard` | every module (the default, and what new projects get) |
| `solo` | everything except `net` and `online`: single-player games. Hosting and joining report that the build has no multiplayer |

The build configuration `Presets` builds the samples with each preset, as CI does. Other combinations and versions are the game's own responsibility; peers with different simulation modules can't join each other.

## Vendored copies and the lock file

The engine repository keeps a copy of every module in `modules/`, so cloning `MealKit` alone is enough to build. `modules.lock` records the repository, tag and commit each copy comes from. An engine version means `VERSION` plus `modules.lock`.

`tools\modules.ps1` keeps them in step:

| Command | What it does |
|---|---|
| `status` | compares each copy with its locked commit |
| `sync [name]` | rewrites copies from the locked commits |
| `bump <name> [tag]` | locks a new tag of a module repo and copies it in |
| `fetch -Project <folder>` | gets the versions a game pins with `engineModuleVersion` |
| `local on [name]` | links `modules/<name>` to the checkout beside the engine (`..\MealKit-<Name>`), for a change that spans repos; `local off` puts the copy back |

A change to a module goes into its own repository first: commit, tag, then `bump` in the engine, so the engine gets the new copy and the lock in one commit. Each module repository runs the shared workflow `engine-module.yml`, which builds the engine with that repository in place of its copy.
