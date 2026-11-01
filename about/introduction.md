# Introduction

MealKit is a **3D multiplayer game engine** that stays light and fast on office PCs with Intel integrated graphics.
Today it runs on Windows with DirectX 12. Other platforms are planned for stage 5 of the {engine}`roadmap <docs/ROADMAP.md>`.

## Principles

- **Must have**: 3D and multiplayer.
- A light, fast engine comes before any one game. Games built on the engine may change.
- Many platforms, with DirectX 12 as the reference. OS APIs are called only behind the platform layer (`mealkit/platform/`) and graphics APIs only behind the engine's thin RHI (`mealkit/rhi/`). Features are not lowered to fit another API.
- Goals: release on PC, mobile, web and consoles, editors on Windows, macOS and Linux, and crossplay between all platforms (roadmap stage 5). Simulation code has no platform branches. 2D games are not supported.
- No game is built in the engine repository. Engine features are proven by using them in the reference samples under `samples/`.
- The engine repository builds only deterministic simulation, lockstep networking, the renderer and the editor, and takes everything else from finished external tools and libraries. Authoring tools (Blender, Penpot, Effekseer, VS Code) are used freely.
  Where no free tool fits a role's workflow, MealKit builds a small tool of its own (the first is audio) in a separate repository under the MIT license, opened from the editor. MealKit is this family: the engine and editor in the middle, a tool for each role around it.
  Libraries that ship inside the game are copied into `third_party/` at a fixed version. Libraries that touch the simulation must be verified as deterministic.
- One answer per problem. Design questions such as global access, object composition, pooling and asynchronous work have a single answer in the {engine}`coding model <docs/CODING_MODEL.md>`, and only that answer is used.

## Current state

| Module | Contents |
|---|---|
| Core | Logging, high-resolution clock, frame limiter, math (Vec3/Quat/Mat4, reversed-Z), deterministic math (DetMath), PCG32 random numbers, FNV hash, field declarations (`MEALKIT_FIELD`), Tracy markers |
| Platform | The layer that holds all OS calls (`platform/win32/`, and a minimal `platform/posix/` for headless builds that CI compiles on Linux and macOS): Win32 window, per-monitor DPI, Raw Input, paths and user data folders, child processes, DLLs and file dialogs (editor), images (WIC). `tools\check_platform.ps1` blocks OS calls outside the layer |
| Online | `online::Service`: accounts, friend lobbies, invites, platform relay transport. One backend per build (Steam: game builds with the SDK present; none: everything else, including the Editor build) |
| Render | DirectX 12 forward renderer: instancing per mesh (draw calls = number of mesh kinds), upload ring buffer, shaders compiled at build time (DXC), vertex colors, 16/32-bit indices, PNG screenshots, Tracy GPU timing |
| Physics | Jolt Physics wrapper: boxes, spheres, capsules, convex hulls, ray casts, state hash. Deterministic build |
| Asset | glTF loading (cgltf) + optimization and LOD (meshoptimizer) + model cache |
| Net | Host–client deterministic input lockstep (the host is a player and the relay, no dedicated server): only 8 bytes of input per player per tick, desync detection by state hash, up to 8 players. Transport: UDP (redundant sends, no TCP) or Steam relay. Peers with a different build, scene, models or tuning are refused |
| Scene | Object kinds and fields declared by the game, parent–child hierarchy, environment. Human-readable `.scene` text |
| Game / Sim | `GameInstance` and `GameContext` (the boundary to game code), `Simulation<World>` (fixed ticks, interpolation, shadow simulation, recording and rewind), tuning (`.tuning`), project settings, `Pool<T>`, `TickTimer`, `TickEvents` |
| Editor | The general-purpose editor `MealKitEditor` (Dear ImGui + ImGuizmo, Korean and English): project manager, game DLL hot reload, docking panels, scene tree, inspector, gizmos, click selection, undo, autosave, model picker, tuning, state and project settings panels, play mode (several players, pause, rewind), game code and release builds |

Measurements (Intel Core Ultra 5 125U integrated graphics, 1280×720, vsync off, Release, 2,000 boxes + 9 models):

| Item | Value |
|---|---|
| Frame | about 3,500 fps (0.28 ms), 4 draw calls |
| Simulation (Jolt, per tick) | about 2.5 ms while falling → about 0.9 ms once stacked and asleep |
| 4-player network (8,000 boxes) | about 5 KB/s total sent by the host, independent of the number of objects |
| Executables | shipped game about 1.4 MB (static CRT, no redistributable needed). Editor: `MealKitEditor.exe` 1.8 MB + `mealkit.dll` 2.7 MB, game DLL about 0.1 MB |

The performance budget for the minimum spec is in {doc}`../manual/performance`.

## Voice chat

Voice chat is not in the engine core. For friends playing together, **Discord calls are recommended**.
The runtime cost is small (encoding takes 1–2% of one CPU core, about 3 KB/s per speaker), but the development cost (microphones, echo cancellation) is large.
If it becomes necessary, **Steam Voice will be added as an optional module** on top of Steamworks.

## What's next

The plan and its order are in the {engine}`roadmap <docs/ROADMAP.md>` ("Recommended order"), decisions and postponed features in the {engine}`decision log <docs/DECISIONS.md>`, and details of finished items in the {engine}`changelog <docs/CHANGELOG.md>`.
The engine has finished stage 3 (v0.7, solid multiplayer) and is in stage 4 (gameplay framework and tools).
