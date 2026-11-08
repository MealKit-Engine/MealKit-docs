# Source layout

```text
engine/core/                   the kernel: core (Types, Log, Memory, Services, Modules, DetMath, Reflect, ...), platform (Window, Paths, Socket, ...;
                               win32/ and posix/ implementations), jobs (job system, Jolt allocator hooks)
engine/libs/mkui/              game UI runtime library (no MealKit headers)
engine/shaders/                HLSL shared by the renderer (Bindless.hlsli, Forward.hlsl, ...)
engine/res/                    editor icon, editor UI translations (strings/ko.txt)
engine/tests/Tests.cpp         engine unit tests (mealkit_tests.exe)
engine/tools/SimCheck.cpp      determinism rule check for a game's sim/ folder (run at build time by mealkit_add_game)
modules/<name>/                engine modules, each a vendored copy of its own repo (modules.lock):
  engine-module.txt            manifest: kind (sim, view, tool), requires, optional
  include/mealkit/<name>/      headers other modules and games include ("mealkit/<name>/X.h")
  src/mealkit/<name>/          the module's own code and private headers
  editor/mealkit/editor/       the module's editor panels (Editor builds only)
                               sim modules: physics, sim, data, scene, asset, session (the session interface and LocalSession), net (lockstep)
                               view modules: rhi, render, input, audio, ui, loc, settings, feedback, camera, online (+ online-steam, online-eos), game
                               tool modules: debug, live, editor (MealKitEditor)
samples/sandbox/               reference sample (physics party versus) = template for new projects (source/ in a project); its own mealkit.project, assets/
  sim/                         deterministic simulation: World (state, step order, hash), Systems.h, Pawns (slots, controllers, pawns, AI), Props, Objects, Tuning
  view/                        Camera, LocalInput (controls → GameInput), Draw, Effects (tick events → screen effects); only reads sim/ state
  app/                         GameSession (one match, GameInstance implementation), main.cpp (shipped exe), GameModule.cpp (editor DLL entry point),
                               Headless.cpp (headless entry point: match start and bot input, also used by GameSession)
  replays/                     fixed input recordings that CI replays on every build
samples/coop/                  reference sample (co-op third person: terrain, chasers, active ragdolls, revives); same layout, not a template
third_party/                   external libraries (VERSIONS.txt)
cmake/MealKit.cmake            shared build settings, presets + mealkit_add_game() (used by the engine repository and game projects)
cmake/MealKitExport.cmake      release folder creation (game_export target)
cmake/FixExportsDef.cmake      removes MSVC CRT weak alias lines from the mealkit.dll export list (Editor build)
templates/project/             build file templates for new game projects
tools/                         new_project.ps1, upgrade_project.ps1, modules.ps1, check.ps1, check_modules.ps1, mp_test.ps1, ... (and the build scripts)
modules.lock                   the module repos, tags and commits this engine version is built from
VERSION                        engine version (compared with engineVersion in mealkit.project)
```

## Frame flow

1. `Window::pumpMessages`: collect input.
2. `MatchService::update`: the session (`session::LocalSession` for solo play and replays, `net::LockstepSession` otherwise) receives packets, confirms inputs, sends.
3. Simulation: fixed 30 Hz ticks. **Only confirmed ticks** run (Jolt takes 2 steps per tick), and right after a tick runs, the local input is submitted for `tick + inputDelay`.
4. Rendering: interpolate between the previous and current tick, collect into `DrawList`, and draw each mesh once.

## External libraries

The canonical list of external libraries (version, license, where they are used and why) is {engine}`third_party/VERSIONS.txt`. Library licenses are in `THIRD_PARTY_NOTICES.txt`.
The conditions for adding a library are in {doc}`contributing`. How the engine is split into modules is in {doc}`engine_modules`.
