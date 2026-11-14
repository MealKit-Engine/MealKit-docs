# Writing modules

The rules for making a source module and listing it in the registry. How games use modules is in {doc}`../manual/modules`.

Every module is equal: there are no official modules. Each module is one git repository (the name `module-<name>` is recommended), and the registry repository [MealKit-Modules](https://github.com/MealKit-Engine/MealKit-Modules) lists them all.

## Starting a module

Start from the registry's template:

```bat
python tools/new_module.py <name> <folder> --author "<you>" --owner <github owner>
```

The repository root is the module folder. When a game adds the module, these are copied into `modules/<name>/`:

| Path | What |
|---|---|
| `module.txt` | Module information (below) |
| `LICENSE` | Required. The template uses MIT |
| `sim/` | State (`MEALKIT_STRUCT`) and system functions. Deterministic, checked by SimCheck |
| `view/` | Drawing, view model helpers, effects |
| `app/` | Screens and session code the game calls from its own `app/` (through `ctx.match`). Built like `view/`, never into the headless build; no `main` or game module macro |
| `assets/<kind>/` | Only the kind folders of a project's `assets/` (`ui/`, `tables/`, `sounds/` and so on). Text for the module's screens goes in `assets/strings/<language>.txt`, read under the project's own table |
| `art/` | Source files of external tools. Not shipped, not in the content hash |
| `docs/index.md` | The module's documentation in English; `docs/index.ko.md` is an optional Korean version |

`tests/`, `.github/` and build folders stay in the module repository. The game still owns its `app/` (main, game module, its `GameInstance`) and calls the module's `app/` code from there. Keep one feature per module and split big features into small modules with requirements.
`tools\check_layout.ps1` checks a module folder with the same rules as a project.

## `module.txt`

```text
@format module 1
name cooldown
version 0.1.0
engine 0.5
title Cooldowns
summary Tick-based cooldowns for skills and actions, with a fill bar .ui component
tags gameplay timer ui
requires
```

| Key | Meaning |
|---|---|
| `name` | Folder name, C++ namespace and asset path prefix. Lowercase letters, digits and `_`. The registry gives each name to the first module that registers it |
| `version` | Semantic version. Must match the repository tag `v<version>` |
| `engine` | Engine `MAJOR.MINOR` the module is made for. Before 1.0 the minor version is the API boundary; the build warns when it differs |
| `requires` | Required modules as `name minimum-version`, separated by spaces |
| `title`, `summary`, `tags` | Shown in lists and search |

## Code rules

- All code is in `namespace <name>`. Include module files from the `modules/` folder: `#include "cooldown/sim/Cooldown.h"`.
- **A module does not know the game.** System functions take only the module's state, the tick number, the module's tuning and engine core types (`Pool`, `Id`, physics queries). Results go back as return values or as a result array in the module's state, never through callbacks.
- **A module never runs by itself.** The game puts the state in its `WorldState` and calls the functions from `World::step()`. Write the code to paste in the "Adding" section of your documentation.
- Tuning is your own `MEALKIT_STRUCT Tuning` with default values. The game nests it in its `Tuning`, so it ends up in `game.tuning`; screen values go the same way in `view.tuning`. There is no tuning file of your own.
- A module includes only the engine's public headers (the list in {engine}`engine/public_headers.txt`, which v1.x keeps source compatible). A module `sim/` file may include the engine core, its own `sim/` and the `sim/` of modules in `requires`. SimCheck reports SIM013 when it includes the game's `source/` and SIM014 when it includes a module that is not in `requires`, on top of the usual simulation rules.
- Asset paths are `modules/<name>/<kind>/...` (resolved to `modules/<name>/assets/<kind>/...`). A table example: `MEALKIT_TABLE(ItemDef, "modules/inventory/tables/items.table", 0)`.
- Games may change your files. Keep components small so that a game can copy one into its own `assets/` instead.

## Tests and CI

`tests/` holds unit tests with their own `CMakeLists.txt` that links the engine core, so a module builds without a game:

```bat
cmake -S tests -B build/tests -G Ninja -DMEALKIT_ROOT=<engine folder> -DMEALKIT_HEADLESS_ONLY=ON
```

The template's workflow is one line that calls the registry's shared workflow (`MealKit-Engine/MealKit-Modules/.github/workflows/module.yml@v1`). On Windows and Linux it gets the newest engine tag for `engine`, checks `module.txt`, `LICENSE` and `docs/index.md`, builds and runs `tests/`, and runs SimCheck on the module. Run the same check locally from a compiler prompt:

```bat
powershell -File tools/check_module.ps1 -Module <module folder> -Engine <MealKit folder>
```

## Documentation

`docs/index.md` is one page with these sections: overview, Adding (the code to paste), Usage, How it works (algorithm and determinism notes), Version history. The registry site draws it for every version, and games get the matching copy with the module. Relative links point into your repository.

## Publishing and registering

1. Make the repository public, push, and tag the version: `git tag v0.1.0` (the same as `version`).
2. Open a pull request on MealKit-Modules that adds `entries/<name>.txt`:

   ```text
   @format module-entry 1
   name cooldown
   repo https://github.com/KingProtea99/module-cooldown
   author KingProtea99
   ```

3. CI checks the entry and every `v*` tag, then builds the newest one. A person merges the pull request after CI passes. CI does not review the code.

The entry holds only the name and the repository; everything else comes from your tags and `module.txt`. New versions need no pull request: push a new tag and the daily run adds it to `index.json`. The list records each tag's commit, so never move a tag that is listed; publish a new version instead.
