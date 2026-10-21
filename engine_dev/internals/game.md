# Game

This page explains how the game folder works inside: the boundary between the engine and game code, the main loop of the shipped exe, the simulation runner, headless runs, input recordings and the small data services (tuning, project settings, match start data, saves, performance numbers).
The code is in {engine}`engine/src/mealkit/game`. `game` is the last engine folder before `editor` in the layer order ({engine}`docs/CODING_MODEL.md` "엔진 폴더 사이 의존"), so it may include every other engine folder, and only the editor includes it.

Part of the folder belongs to the engine core (`mealkit_core`), which runs without a window: `GameInstance.h`, `GameContext.h`, `GameData`, `GameOptions`, `Headless`, `InputRecord`, `ProjectSettings`, `Save`, `Loadout.h`, `WorldSnapshot.h`, `SimDebug.h` and `Simulation.h`.
The rest needs the screen side and is only in the windowed engine: `Frontend`, `GameMain` and `FrameStats` ({engine}`engine/CMakeLists.txt`).

How to use these from a game is in {doc}`../../manual/projects`, {doc}`../../manual/multiplayer` and {doc}`../../manual/settings`. How the editor uses them is in {doc}`editor`.

## The game code boundary

A game implements one class, `game::GameInstance` ({engine}`engine/src/mealkit/game/GameInstance.h`), usually `app/GameSession`. It is one match: it runs the deterministic simulation, reads local input, moves the camera and fills the draw list.

| Function | Called |
|---|---|
| `lobby` | Every frame before the match starts (once before an offline session opens). The game sets this player's match start data. |
| `start` | Once per match, one frame after the session becomes `Running` (that frame draws the loading screen). |
| `stop` | Once when the match is over: back to the lobby, left, or disconnected. The next match calls `start` again. |
| `menus` | `true` if the game draws its own screen flow (title, menus, lobby, results). The engine then starts at the menu when no room is given on the command line and leaves `Esc` and `Enter` to the game. |
| `update` | Every frame: camera input and simulation ticks. |
| `buildFrame` | Every frame: fills the frame parameters and the draw list. |
| `nextTick`, `stateHash`, `finished`, `captureDue`, `takeSimMsPerTick` | By the engine loop for automated tests and performance numbers. |
| `setTuning`, `stateView`, `debug` | By the editor: live tuning, the State panel, and pause and rewind. |
| `debugUi` | Inside the Dear ImGui frame, in development builds and the editor. |

The engine passes a `game::GameContext` ({engine}`engine/src/mealkit/game/GameContext.h`) to each call. It holds references to the engine services the screen side uses: window, renderer, models, lockstep session, the match service, audio, feedback, input actions, strings, game UI and player settings.
It also holds values the engine sets every frame: the viewport, whether the game may read the keyboard and mouse, the display tuning and the user folder.
The game does not keep the context, and `sim/` never receives it: the simulation only gets `World&`. The reasons are in {engine}`docs/CODING_MODEL.md` "엔진 기능에 어떻게 접근하나".

The same game class is used in two ways:

- **The editor** loads it from a game DLL through `game::GameModule`, a table of plain function pointers returned by `mealkitGetGameModule` (the `MEALKIT_GAME_MODULE` macro). {doc}`editor` lists the entries.
- **The shipped exe** links the game class directly. `gameModuleOf<GameClass>` builds the same table, so the exe main reads object types, tuning type and tables the same way the editor does.

`kApiVersion` (now 20) is raised whenever the promise across the DLL boundary changes. The comment above it lists what each version added. The editor refuses a DLL whose version differs.

Optional types are found at compile time. If the game class declares `ProjectSettingsType`, `ViewTuningType` or `EventType`, the matching module entry returns its type information; otherwise it returns `nullptr`. This uses C++20 `requires` expressions, so a game declares only what it uses.

## The shipped exe main

A game's `app/main.cpp` is one line:

```cpp
MEALKIT_GAME_MAIN(sandbox::GameSession, sandbox::Headless)
```

The macro writes `main` ({engine}`engine/src/mealkit/game/GameMain.h`). If the arguments contain `--headless`, it calls the headless entry point; otherwise it calls `game::runGame` ({engine}`engine/src/mealkit/game/GameMain.cpp`).
`gameMainSpec` also takes the headless class's `defaults` function, so the windowed exe and the headless binary get the same default port and player count from the game's project settings. A `static_assert` checks that both classes use the same `ProjectSettingsType`.

`runGame` starts in this order:

1. Parse the command line with `parseGameArgs` (`--help` lists the options). `--system-info` prints the CPU and GPU and exits.
2. Create the window, the renderer and the model cache.
3. Call `loadMatchData` (see "Match data and tuning" below): `mealkit.project` with the game's `game.*` lines, the start scene (or `--scene`), the tuning and the content hash. Then apply the headless defaults and set the content hash on the lockstep session.
4. Create the `MatchService` (which owns the lockstep session) and open what the command line asks for: host, join or a Steam lobby. Solo play starts a match at once for games without menus, for `--exit-tick` runs and for `--bot`; a game with menus otherwise starts at its title.
5. Create the game, start audio and feedback, and initialize the `Frontend`.

Then it runs one loop. Each frame:

1. Handle engine keys: `Esc` quits a game without menus (unless the settings screen is open), `V` toggles vsync, `F12` saves a screenshot, `F1` toggles the debug UI in development builds, `I` opens the friend invite in an online lobby.
2. Update the match service (online lobby, session, LAN room announcements and search). Before the match, call `game->lobby`. The host starts the match when `--auto-start` players are in, and a game without menus also on `Enter`.
3. One frame after the session becomes `Running`, call `game->start`; when it stops being `Running`, call `game->stop`.
4. Set the viewport and input permission (the window must have focus, and the debug UI may take input), then `front.update` and `game->update`.
5. Update audio and feedback.
6. Unless the window is minimized: `game->buildFrame`, `front.afterBuildFrame`, draw the 3D scene, the game UI, then the debug UI on top.
7. Wait for the frame limiter, then update `FrameStats`. Four times a second the window title shows the lobby state or the performance line.

Delta time is capped at 0.25 seconds, so a long stall does not become a huge step.

### Automated runs

With `--exit-tick`, the run is automated: error dialogs are off, player settings use defaults and are not saved, and there is no user folder.
When the game reaches the exit tick, `reportFinish` prints lines that test scripts read:

```text
FINAL tick=<t> hash=<16 hex digits> desync=<0|1>
SHADOW ok|DESYNC tick=<t>                      (with --shadow)
REWIND ok|FAIL ticks=<a>..<b> memory=<MB> ...  (with --rewind-test)
```

`--rewind-test` pauses, seeks through the whole recorded range in steps of 37 ticks, returns to the live tick and checks that the hash is unchanged. The exit code is 0 for success, 2 for a network desync, 3 if the session ended early, 4 for a rewind failure and 5 for a shadow desync.
The exe waits one more second before closing, so peers receive the last tick.

## Build information

{engine}`engine/src/mealkit/game/BuildInfo.h` describes the running build: the game version (`version` in `mealkit.project`), the git commit of the project folder (`+` when files are changed) and the simulation version. `cmake/BuildInfo.cmake` writes them into `mealkit_build_info.h` on every build, rewriting the file only when it changes. The simulation version hashes the game version and every file that reaches the simulation, with line endings made LF and paths made relative, so another OS or compiler gets the same value from the same sources.
Only game targets see that header, so the engine macros that expand in game code (`MEALKIT_GAME_MAIN`, `MEALKIT_GAME_MODULE`, `MEALKIT_HEADLESS_GAME`) read it through `MEALKIT_THIS_BUILD` and pass it to the engine (`GameMainSpec::build`, `GameModule::build`). The exe logs it at start and shows the version in the window title.

## Match service

`game::MatchService` ({engine}`engine/src/mealkit/game/MatchService.h`) owns the lockstep session and is what a game's menus call through `ctx.match`: `playOffline`, `host`, `hostOnline`, `join`, `joinOnline`, `start`, `returnToLobby`, `leave`, `setBrowsing` and `rooms`. The exe, editor play and player windows each create one; the command line uses the same calls.
`phase()` maps the session state to what the screen flow needs (menu, opening an online lobby, connecting, lobby, running, ended). `update` runs the online service, opens the session when an online lobby is ready (owner hosts on the platform relay, others join it), joins an accepted invite from the menu, updates the session, announces a hosted lobby on the LAN, and refreshes the room list while browsing.
The default player name is the online account name, otherwise the computer's user name (`userName()`); a game can set another with `ctx.session.setLocalName`.

## Frontend

`game::Frontend` ({engine}`engine/src/mealkit/game/Frontend.h`) is the set of screen services that every windowed host of a match owns: the shipped exe, editor play and the editor's player windows. Each one calls it in the same order, so input, UI and settings behave the same everywhere.

It owns the input actions and gamepads, the game strings, the game UI system, the player settings service and the live display tuning. Audio and feedback are owned by the host, because the editor also uses them for its Sound and Feedback previews.

- `init` loads key bindings (the project's file plus the player's changed keys), strings, UI and settings. Calling it again loads them again.
- `context` builds a `GameContext` that points at these services.
- `update` runs before `game.update` every frame. The UI updates first: if it wants the mouse or keyboard, the frame's permission flags are turned off, so a click on a button does not also reach the game. Then the settings screen updates, and last the input actions are sampled.
- `afterBuildFrame` passes the camera to world-space UI, puts the audio listener at the camera, and adds the feedback screen tint.
- `renderUi` draws the game UI after the 3D scene and before the debug UI.
- Subtitles: while the audio engine has subtitle lines and the player setting is on, `update` opens the standard screen `ui/subtitles.ui` (when the project has it) at layer 5 and fills `SubtitlesVm` with the last four lines from the string table.

The editor passes `nullptr` for the display window, so player settings such as window mode and frame cap do not change the editor window.

## The simulation runner

`game::Simulation<World>` ({engine}`engine/src/mealkit/game/Simulation.h`) runs the game's `World` at a fixed tick. The game's `GameSession` owns one. It is a template, so the game's world type is known at compile time and the class is `final`.

The world must have `state` (a `MEALKIT_STRUCT` with a `tick` field), `physics`, `events`, `step(const net::TickInputs&)` and `hash()`. A `static_assert` refuses a state that contains `std::string`: names belong in tuning or scene data, and the state uses ids.

### Fixed tick

`update` adds the frame's `dt` to an accumulator and runs ticks while the accumulator holds at least one tick, up to 8 ticks per frame (`kCatchUpTicks`).
A tick runs only when the lockstep session has every player's input for it (`canExecute`). While waiting for input, the accumulator is capped at 8 ticks, so time debt does not grow without end.

One tick follows the lockstep order:

1. Take the confirmed inputs for this tick from the session.
2. Copy the current state to `previous`, then call `World::step`.
3. Hash the state and report it to the session (`tickExecuted`), which compares hashes between peers.
4. Write the input recording and hash log if they are open, step the shadow world, and record history (below).
5. Call the game's `onTick` so it moves this tick's events to the screen side. Events are cleared by the next `step`, so this happens after every tick, not once per frame.
6. Sample local input and send it for tick `next + inputDelay`.

The rules behind the order are in {engine}`docs/CODING_MODEL.md` "흐름".

### Interpolation

The screen draws between two ticks. `previous()` is the state before the last tick, and `alpha()` is the accumulator divided by the tick length, clamped to 0..1.
The view lerps positions from `previous` to the current state with `alpha`. When paused, `alpha` is 1, so the screen shows the exact tick.

### Pending inputs

The runner keeps the local inputs it has sent but not yet run (`forEachPendingInput(f)`, target tick order). With an input delay of n ticks there are n of them. A game uses them to draw only its own character ahead by those inputs, which hides the input delay without touching the simulation: the example adds the moves of the pending inputs (speed × one tick each, capped at 1.5 m) to its own character, camera and name tag, and eases toward that offset (`view.tuning` `prediction`). When the confirmed state catches up, the offset shrinks on its own. Pushes, jumps and collisions with others still appear when they are confirmed.

### Shadow simulation

With `PlayOptions::shadow`, `start` creates a second `World` and resets it with the same reset function (with one physics thread, which does not change the result).
Every tick steps it with the same inputs and compares `hash()`. On the first difference, the runner stops comparing, lists the differing state fields with `reflect::diffStruct` (at most 24), logs them and pauses.
An empty list means only the physics state differs. This finds uninitialized values, global state, pointer order and wall clock reads inside one process. It doubles the simulation CPU.

### Recording, snapshots and rewind

With `PlayOptions::record`, every tick's inputs and hash are kept in queues, and a snapshot is taken every 150 ticks (`kSnapshotInterval`, 5 seconds at 30 Hz). The newest 40 snapshots are kept (`kKeepSnapshots`), and inputs older than the first snapshot are dropped.

`seek(tick)` works only while paused:

1. On the first seek, the live state is saved in its own snapshot, so the runner can return to it.
2. It loads the latest snapshot at or before the target tick.
3. It runs the recorded inputs up to the target, comparing every tick's hash with the recorded hash.

A snapshot that does not restore to its saved hash, or a replayed tick with a different hash, sets `replayError`. Both mean there is state not declared with `MEALKIT_FIELD`, or the code is not deterministic.
Resuming or stepping past the end returns to the live snapshot.

`modifyWorlds` changes the real and shadow worlds the same way (for example a live tuning change) and clears the history, because old inputs would no longer reproduce the new state.

The editor controls all of this through `game::SimDebug` ({engine}`engine/src/mealkit/game/SimDebug.h`): `timeline` (first, live and viewed tick, paused, memory used), `setPaused`, `stepOnce`, `seek`, `shadow` and `replayError`. `GameInstance::debug()` returns the runner, or `nullptr` if the game has none.

## World snapshots

`game::WorldSnapshot` ({engine}`engine/src/mealkit/game/WorldSnapshot.h`) is the tick, the hash at save time, the declared state as bytes, and the physics snapshot.

- `saveSnapshot` writes the state field by field with `reflect::saveStruct` and saves Jolt's state with `physics.save`.
- `loadSnapshot` reads them back and returns `false` if the bytes do not fit or the hash after restoring differs from the saved hash.

Values outside `state` and `physics` (spawn points, tuning copied at match start) are not saved, because they do not change during a match.
The hash check on load makes undeclared state visible at once instead of a silent difference later.

## Headless runs

`game::runHeadless<Game>` ({engine}`engine/src/mealkit/game/Headless.h`) runs a match with no window, renderer or audio. Input always comes from the game's bot function. It is used for the CI determinism comparison, rule tests and network tests.

A game writes a class in `app/Headless.cpp` and the line `MEALKIT_HEADLESS_GAME(sandbox::Headless)`. The class gives `World`, `TuningType`, `kTickDt`, `startWorld` and `botInput`, and optionally `ProjectSettingsType`, `botCommands`, `botLoadout` and `defaults`. `GameSession` uses the same `startWorld` and `botInput`, so the headless match is the windowed match without a screen.

The macro defines `mealkitHeadlessMain`, which the shipped exe calls for `--headless`. In the `<game>_headless` target (`MEALKIT_HEADLESS_TARGET`) it also defines `main`.
That target is built from `sim/` and `Headless.cpp` only and links only `mealkit_core` ({engine}`cmake/MealKit.cmake`). This is why it builds on Linux and macOS with Clang or GCC, and why the layer order matters: the core folders never include the screen side.

The headless loop is like `runGame` without drawing:

- `loadMatchData` reads the project, the scene, the tuning and the models (CPU data only) and builds the content hash, the same call the exe makes, so a headless peer can join a windowed one. The loop flattens the scene once for the simulation.
- The host starts the match when `--auto-start` players are in the lobby.
- Every iteration passes a frame time of 8 ticks, so the runner catches up as fast as possible.
- Offline runs never sleep. Network runs sleep 1 ms only when no tick ran in that iteration (waiting for input), so peers on a runner with few cores leave time for each other's physics threads.

At the exit tick it prints the same `FINAL` and `SHADOW` lines as the exe. How to run it is in {doc}`../../manual/multiplayer` and {doc}`../testing`.

## Input recordings and hash logs

{engine}`engine/src/mealkit/game/InputRecord.h` writes two kinds of files.

- **Hash log** (`--hash-log`): one line per tick, `<tick> <hash in 16 hex digits>`. If two runs write the same file, their states were equal on every tick.
- **Input recording** (`--record-inputs`): the confirmed inputs and the state hash of every tick. `--replay-inputs` runs them again and compares.

The recording starts with `MKINPUT1`, the format version (now 3), player count, seed, match data, the content hash and every player's match start data. Then, per tick: 8 bytes of input per player, the command bytes with a 2-byte length, and the 8-byte hash.
All numbers are written byte by byte in little endian, so the file is the same on every CPU. The writer opens the file on tick 0, because the match values are only fixed when the session becomes `Running`.
The reader stops at the first incomplete tick, so a file cut off by a crash is still usable up to that point. It also reads versions 1 (no commands) and 2 (no match start data).

`replayHeadless` loads the recording, builds the world from the recorded match values (`MatchInfo`), steps through every recorded input without a network, and prints `REPLAY ok` or `REPLAY DESYNC tick=<first mismatch>`. It warns when the content hash differs, because then the hashes will differ too.

The CI uses these files: each build replays the recordings in `samples/*/replays/*.rec` with a hash log, and `tools/ci_compare.ps1` checks that every build (Windows MSVC and clang-cl, Linux, macOS) wrote the same hashes ({engine}`.github/workflows/ci.yml`).
Feeding one recorded file to every build, instead of running bots on each, is what makes the builds comparable. `tools/record_replay.ps1` makes the recording again when the simulation result changes on purpose.

## Match data and tuning

{engine}`engine/src/mealkit/game/GameData.h` loads what a match is made of, the same way in the exe, the headless binary and the editor.

- `loadMatchData` is the one call that loads a match: the project settings (found next to the exe, or given by the editor), the game's `game.*` values, the scene (a given scene, a given file, or the start scene; a built-in arena if there is no file), the tuning, and the content hash. The game types come in a `GameTypes` value: `gameTypes(module)` for the exe and the editor, the game class for the headless binary. Because the exe, the headless binary, editor play and the player windows all call it, they cannot pass different things to the hash.
- `loadTuning` reads `assets/game.tuning` (or a given path) into the game's tuning type. A missing file keeps the declared defaults and logs a warning.
- `LiveTuning` holds the display tuning (`assets/view.tuning`). `poll` checks the file time at most every 0.25 seconds and reads the file again when it changed. It reads into a fresh value, so a deleted line goes back to its default. If the file does not exist yet, it watches the path next to `game.tuning`.
- `contentHash` is the hash peers compare before a match. It hashes the parts of the scene that affect the game, the model files, the tuning values, the project settings except view fields, and the simulation tables.

The display tuning is not in the content hash, so it can change during a multiplayer match. Where each kind of number belongs is in {engine}`docs/CODING_MODEL.md` "숫자는 어디에 두나".

## Project settings

`game::ProjectSettings` ({engine}`engine/src/mealkit/game/ProjectSettings.h`) is the engine part of `mealkit.project`: name, engine folder and version, start scene, icon, creation date, sound voices, default language, the simulation tick rate (`tickRate`, hashed), the automatic input delay (`inputDelayAuto`, `inputDelayMinMs`, `inputDelayMaxMs`), the GPU budget per pass for the benchmark report (`gpuBudget*Ms`) and the asset budgets per model kind (`budget*`, passed to `ModelCache::setBudgets` through `modelBudgets`).
`applyTickRate` makes the project's tick rate the process tick rate (`reflect::setTickRate`, 10 to 120) before any time field is read: `loadMatchData`, `loadGameProject` callers and the editor's project loading call it. `tickDt()` and `msToTicks()` convert with it; the headless loop and the example's `GameSession` take the tick length from `tickDt()`, and `--delay` is in milliseconds. A game adds its own struct, saved in the file with the `game.` prefix.

The file uses the same `path value` lines as tuning files, and the reader also accepts old `key=value` lines. Loading keeps three things the engine cannot type-check:

- `game.*` lines are kept as text, so the editor can save the file before the game DLL is loaded without losing them.
- Unknown keys (written by a newer engine) are kept and written back.
- Comment lines before the first key are kept as the header.

`loadGameProject` finds `mealkit.project` with `findAsset`, so it works next to the exe in a release folder and in the project folder during development.
Only fields that affect the simulation enter the content hash; others are declared with `MEALKIT_VIEW_FIELD`. `userFolder` returns the per-player folder (the user data folder plus the game name) for changed keys, settings and saves.
See {doc}`../../manual/projects`.

## Match start data

{engine}`engine/src/mealkit/game/Loadout.h` sends values a player brings into a match, such as a chosen character.
In the lobby the screen side calls `setLoadout(session, value)`. The host fixes everyone's data when the match starts and sends it to all peers. `startWorld` reads it with `readLoadout(match, player, value)` and copies it into the world state, so it is part of the hash and snapshots.

The value is sent with `memcpy`, so the type must be trivially copyable (no strings, containers or pointers), checked by `static_assert`. With its 4-byte header it must fit in `net::kMaxLoadoutBytes` (128).
The header is the FNV-1a hash of the type name, so data of another type is refused and the default stays. The data is also written into input recordings, so a replay starts with the same choices. See {doc}`../../manual/multiplayer`.

## Saves

{engine}`engine/src/mealkit/game/Save.h` saves progress that lives outside a match (unlocks, statistics) as one `MEALKIT_STRUCT`, in `saves/<name>.save` in the user folder.

- The file is text: a comment line with the type name, `version <n>`, then `path value` lines.
- Reading drops fields the type no longer has and leaves missing fields at their defaults. A file with a lower version is passed to the game's `migrate` function first, which can rewrite the lines. A newer version is read with a warning.
- Writing copies the previous file to `.bak`, then writes through `writeTextFile`, which writes a temporary file and renames it over the old one, so a crash during the write does not break the save.
- An empty user folder (automated runs, editor player windows) means nothing is read or written.

The simulation never reads save data. See {doc}`../../manual/settings`.

## Performance numbers

`game::FrameStats` ({engine}`engine/src/mealkit/game/FrameStats.h`) collects the numbers each subsystem measures with its own `stats()`: frame time, simulation time per tick, tick, players, round trip time and bandwidth, desync, draw calls and instances, GPU time per pass, and sound voices.
`update(dt, sources)` is called every frame. It adds up the renderer's GPU times every frame. When a period ends (0.25 seconds by default) it averages the frame and GPU times, keeps the worst frame and the 99th percentile frame (`frameMsPercentile`), reads every source that is not `nullptr`, and returns `true`.
With a renderer it also reads the process memory (platform layer `processMemory`) and the GPU memory (`Renderer::gpuMemory`, a driver query, so once per period).

`game::Benchmark` ({engine}`engine/src/mealkit/game/Benchmark.h`) is the `--benchmark` mode of the shipped exe. `runGame` turns on the bot, a fixed seed and vsync off before the loop starts.
Every frame the loop passes the frame time, whether a match is running and the `FrameStats` sample that just ended (if any). After the warm-up it keeps every frame time (for the 1% worst frame over the whole run) and weights each sample by its length.
When the time is up, `report` writes the text with the GPU budget table from `mealkit.project` and `summaryLine` the `BENCHMARK` line. It builds on `FrameStats` instead of reading the subsystems again, because `takeSimMsPerTick` may only have one reader.

`line()` joins the items with ` | ` for the window title and the `perf:` log, and `lines()` puts one item per line for the `F1` overlay. The editor status bar uses the same class.
`takeSimMsPerTick` empties its average when read, so only `FrameStats` calls it, and every display shows the same numbers. See {doc}`../../manual/performance` and {engine}`docs/CODING_MODEL.md` "성능 숫자 모으기와 보여 주기".

## Techniques used

The algorithms and patterns behind the parts above, with where to find them in the code.

### Boundary and main loop

| Technique | Where | What it does |
|---|---|---|
| Versioned C ABI | `GameModule`, `kApiVersion` | A table of plain function pointers behind one `extern "C"` function, checked by a version number, so DLLs from another build are refused instead of crashing. |
| One table for two link modes | `gameModuleOf<GameClass>` | The exe links the game class directly but builds the same module table as the DLL, so both read game types in one way. |
| Compile-time optional members | `gameProjectSettingsType`, `gameViewTuningType`, `gameEventType`, `runHeadless` | C++20 `requires` expressions detect whether the game declares a type or function, so optional parts need no registration. |
| Service context (dependency passing) | `GameContext` | Engine services are passed into every call instead of being global, and the simulation never gets them. |
| Shared frame order | `Frontend` | The exe, editor play and player windows call the same steps in the same order, so screen behavior cannot drift between them. |
| Input capture by priority | `Frontend::update` | The UI takes the mouse and keyboard first and turns off the game's permission flags for that frame. |
| Clamped delta time | `runGame` | A frame time above 0.25 seconds is cut, so a stall does not become one huge step. |

### Simulation

| Technique | Where | What it does |
|---|---|---|
| Fixed timestep with accumulator | `Simulation::update` | Frame time is added to an accumulator and spent in whole ticks, at most 8 per frame, with the debt capped while waiting for input. |
| Render interpolation | `Simulation::alpha`, `previous` | The screen draws between the previous and current tick with the leftover fraction of a tick. |
| Deterministic lockstep order | `Simulation::executeTick` | A tick runs only with every player's confirmed input; local input is sent for a later tick (input delay). |
| Dual execution (shadow simulation) | `Simulation` with `PlayOptions::shadow` | A second world steps with the same inputs, and the hashes are compared every tick. |
| Structural diff | `reflect::diffStruct` | Lists the declared fields that differ when the shadow world diverges. |
| Checkpoints and replay | `Simulation::seek`, `takeSnapshot` | Periodic full snapshots plus every tick's inputs. A past tick is rebuilt from the nearest earlier snapshot by replaying inputs. |
| Bounded history | `takeSnapshot` | Keeps the newest 40 snapshots and drops inputs before the first one. |
| Verified restore | `loadSnapshot` | Compares the hash after loading with the hash saved with the snapshot, which exposes undeclared state. |
| Reflection-based serialization | `saveSnapshot` | Writes the declared state field by field, so padding and undeclared members never enter a snapshot. |

### Records and data

| Technique | Where | What it does |
|---|---|---|
| Portable binary format | `InputRecordWriter`, `put` / `get` | Writes every number byte by byte in little endian, so a file is identical on every CPU and compiler. |
| Versioned format with old readers | `loadInputRecording` | Reads versions 1 to 3, and stops at the first incomplete tick, so a cut-off file is still usable. |
| Golden-file comparison | `tools/ci_test.ps1`, `tools/ci_compare.ps1` | Every build replays the same recording and writes a hash log; the logs must match the reference build. |
| Content hash | `contentHash` | One FNV-1a hash over scene, models, tuning, project settings and tables, compared before peers join. |
| Polling file watch | `LiveTuning::poll` | Checks the file time at most 4 times a second and reloads into a fresh value. |
| Lossless round trip of unknown data | `loadProjectFile` / `saveProjectFile` | Keeps `game.*` lines, unknown keys and the header comment as text and writes them back unchanged. |
| Type-tagged binary blob | `setLoadout` / `readLoadout` | The first 4 bytes are a hash of the type name, so a value of another type is refused. |
| Schema migration | `readSave` with `SaveMigrate` | A version number in the file lets the game rewrite old lines before they are read by name. |
| Atomic file replace | `writeTextFile` in {engine}`engine/src/mealkit/platform/win32/Paths.cpp` | Writes a temporary file and renames it over the target, and keeps a `.bak` of the previous save. |
| Periodic averaging | `FrameStats::update` | Averages frame time over 0.25 seconds and keeps the worst frame, so all displays read one sample. |
