# Modules

A source module is a reusable game feature, such as skill cooldowns or a health bar, that you copy into your project as source code. Modules are not part of the engine: each one lives in its own repository, and you add only the ones your game uses.

Find modules on the registry site, [mealkit-engine.github.io/MealKit-Modules](https://mealkit-engine.github.io/MealKit-Modules/). Each module's page is its own documentation: what it does, the code to connect it, how to use it and how it works.
To make and publish a module, see {doc}`../engine_dev/writing_modules`.

## What a module is

A module is a folder `modules/<name>/` in your project:

| Folder | What |
|---|---|
| `module.txt` | Name, version, engine version, required modules |
| `sim/` | Simulation code. Checked by SimCheck like your own `source/sim/` |
| `view/` | Drawing, view models, effects |
| `assets/<kind>/` | `.ui`, `.table`, sounds and so on, with the same kind folders as your `assets/` |
| `docs/index.md` | The module's documentation for the version you have |
| `module.files` | Written by the module tool: where the module came from and a hash of every file |

The build picks up `modules/*/sim/` and `modules/*/view/` the same way as your `source/`, so you do not change your `CMakeLists.txt`. Module code is in the simulation version, so players with different module code cannot join each other, like any other simulation change.

The list of installed modules is the `modules/` folder itself. Commit it with your project: teammates and CI build without downloading anything.

## Adding a module

In the editor, **File > Modules...** shows the installed modules and the registry list. **Add** copies the newest version made for your engine version, then the editor rebuilds the game code. MealKit Manager has the same list on its **Modules** tab for the selected project. Modules cannot be changed while playing.

The same from the command line, with the engine's `tools\module.ps1`:

```bat
powershell -ExecutionPolicy Bypass -File tools\module.ps1 search cooldown
powershell -ExecutionPolicy Bypass -File tools\module.ps1 add -Project D:\Games\MyGame cooldown
```

- `add <name>@<version>` picks a version. When the module requires other modules that you do not have, the tool lists them; `-WithRequires` adds them too.
- `add` also takes a git address with a tag (`https://github.com/me/module-x#v0.2.0`) or a folder, for modules that are not registered, such as one you are writing.
- `search` works without a project and without a network connection: the last downloaded list is kept in `%LOCALAPPDATA%\MealKit\module-index.json`.

```{warning}
Module code runs inside the editor and the game. The registry checks that a module builds, not what it does. Read the code you add.
```

## Connecting a module

Adding a module does nothing on its own. The engine never registers or calls module code automatically, so the order of every step stays visible in your code, which matters when you debug a desync. Each module's documentation has an "Adding" section with the code to paste. The usual shape:

```cpp
// source/sim/World.h: module state is a field of your simulation state
#include "cooldown/sim/Cooldown.h"

MEALKIT_STRUCT(Pawn) {
    ...
    MEALKIT_FIELD(cooldown::Cooldown, push, {}, "Push cooldown");
};

// source/sim/Pawns.cpp: you call the module where it belongs
if (intent.push && cooldown::tryUse(p.push, world.state.tick, t.pushCooldown.value)) { ... }
```

- Module functions take only the module's own state, the tick and their tuning. They do not know your `World`.
- Because the state is a `MEALKIT_FIELD` of your state, it is in the state hash, snapshots, replays and the editor's **State** panel without extra work.
- A module's tuning is a nested field of your `Tuning`, so its values go in `game.tuning` as `cooldown.<field>`.
- Module assets use the path `modules/<name>/<kind>/...`, for example `use pushBar modules/cooldown/ui/cooldown_bar.ui` in a `.ui` file. Release builds ship the modules' `assets/` folders.

## Updating and changing a module

You may change module files: it is your copy. Updating keeps your changes:

```bat
powershell -ExecutionPolicy Bypass -File tools\module.ps1 list -Project D:\Games\MyGame
powershell -ExecutionPolicy Bypass -File tools\module.ps1 update -Project D:\Games\MyGame cooldown -DryRun
```

- `list` shows each module's version, whether a newer one exists, and how many files you changed.
- `update` replaces files you did not change. For a file you changed, it keeps yours and writes the new one next to it as `<file>.new`; merge them by hand and delete the `.new`. A file removed in the new version is deleted only if you did not change it. `-To <version>` picks a version, `-DryRun` only shows what would happen.
- To restyle a module's `.ui` or table heavily, copy it into your own `assets/` and use your copy. The module file stays unchanged and updates stay easy.
- `remove` refuses while another module requires the module or your `source/` still includes it, and shows the lines (`-Force` removes anyway). Git keeps the old files if you need them back.
