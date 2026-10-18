# Source layout

```text
engine/
  shaders/Forward.hlsl         instance transform + vertex color + half Lambert + hemisphere ambient + fog + selection highlight
  src/mealkit/core/            Types, Log, Clock, Math, DetMath, Random, Hash, Reflect (field declarations), Version, Profile
  src/mealkit/platform/        Window, Input, Paths, Process, System, DynamicLibrary, FileDialog, Image (headers + shared parts)
  src/mealkit/platform/win32/  Windows implementations that call the OS (Win32, Winsock, WIC, dialogs)
  src/mealkit/platform/posix/  minimal Linux and macOS implementation for headless builds (time, files, UDP, logging; built by CI)
  src/mealkit/online/          Online (accounts, lobbies, invites, relay): Steam backend, None backend without an SDK
  src/mealkit/render/          Renderer, Mesh, DrawList
  src/mealkit/physics/         PhysicsWorld (Jolt)
  src/mealkit/asset/           ModelCache (cgltf + meshoptimizer)
  src/mealkit/net/             Socket, Transport, Lockstep
  src/mealkit/scene/           Scene (.scene reading and writing)
  src/mealkit/game/            GameInstance, GameContext (boundary between engine/editor and game code, MEALKIT_GAME_MODULE), Simulation, WorldSnapshot,
                               ProjectSettings, GameData, Headless (MEALKIT_HEADLESS_GAME), InputRecord (input recording and hash logs)
  src/mealkit/sim/             Pool<T>, TickTimer, TickEvents (deterministic tools for the game's sim/)
  src/mealkit/editor/          MealKitEditor: EditorMain, ProjectManager, Project, GameModuleHost (DLL hot reload), Editor, PlaySession, FieldEditor, Strings (tr), ImGuiLayer
  res/                         editor icon, editor UI translations (strings/ko.txt)
  tests/Tests.cpp              engine unit tests (mealkit_tests.exe)
  tools/SimCheck.cpp           determinism rule check for a game's sim/ folder (run at build time by mealkit_add_game)
samples/sandbox/               example game = template for new projects (source/ in a project)
  sim/                         deterministic simulation: World (state, step order, hash), Systems.h, Pawns (slots, controllers, pawns, AI), Props, Objects, Tuning
  view/                        Camera, LocalInput (controls → GameInput), Draw, Effects (tick events → screen effects); only reads sim/ state
  app/                         GameSession (one match, GameInstance implementation), main.cpp (shipped exe), GameModule.cpp (editor DLL entry point),
                               Headless.cpp (headless entry point: match start and bot input, also used by GameSession)
  replays/                     fixed input recordings that CI replays on every build
mealkit.project                project file used when the engine repository is opened as the example game project
assets/scenes, assets/models   scenes and models
third_party/                   external libraries (VERSIONS.txt)
cmake/MealKit.cmake            shared build settings + mealkit_add_game() (used by the engine repository and game projects)
cmake/MealKitExport.cmake      release folder creation (game_export target)
cmake/FixExportsDef.cmake      removes MSVC CRT weak alias lines from the mealkit.dll export list (Editor build)
templates/project/             build file templates for new game projects
tools/                         build_project.bat, new_project.ps1, rename_project.ps1, upgrade_project.ps1,
                               check.ps1, check_platform.ps1, check_strings.ps1, mp_test.ps1, ci_test.ps1, ci_compare.ps1, record_replay.ps1, make_sample_models.py
VERSION                        engine version (compared with engineVersion in mealkit.project)
.vscode/                       build tasks and debug launch configurations
```

## Frame flow

1. `Window::pumpMessages`: collect input.
2. `LockstepSession::update`: receive packets, confirm inputs, send.
3. Simulation: fixed 30 Hz ticks. **Only confirmed ticks** run (Jolt takes 2 steps per tick), and right after a tick runs, the local input is submitted for `tick + inputDelay`.
4. Rendering: interpolate between the previous and current tick, collect into `DrawList`, and draw each mesh once.

## External libraries

The canonical list of external libraries (version, license, where they are used and why) is {engine}`third_party/VERSIONS.txt`. Library licenses are in `THIRD_PARTY_NOTICES.txt`.
The conditions for adding a library are in {doc}`contributing`.
