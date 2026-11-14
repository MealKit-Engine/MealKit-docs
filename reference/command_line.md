# Command line

The example game is called `sandbox`. In a game project, the executables carry the project name. Every program prints its full option list with `--help`.

## Game (`<game>.exe`)

| Option | Meaning |
|---|---|
| `--host [port]` | Host a room and wait in the lobby (default: `game.defaultPort` in `mealkit.project`). Without options a game with menus starts at its title screen |
| `--join <addr[:port]>` | Join a host |
| `--steam` | Host a Steam friends-only lobby (invite with `I` or `Shift+Tab`) |
| `--steam-join <lobby>` | Join a Steam lobby by id (invites from Steam join automatically) |
| `--scene <file>` | Scene to play (default: `scene` in `mealkit.project`) |
| `--tuning <file>` | Tuning values (default `assets/game.tuning`) |
| `--players <n>` | Maximum players when hosting (default: `game.defaultMaxPlayers`, at most 8) |
| `--bodies <n>` | Number of boxes in the example (default: the scene's box spawn areas; set by the host; same as `--match-data`) |
| `--delay <ms>` | Fixed input delay in milliseconds (default: chosen by the host from the players' ping, `inputDelayAuto` in `mealkit.project`) |
| `--seed <n>` | World seed |
| `--vsync <0\|1>` | Vertical sync (default 1) |
| `--fps <n>` | Frame cap when vsync is off |
| `--size <w> <h>` | Window size |
| `--debug` | Turn on the D3D12 debug layer |
| `--local` | Host on 127.0.0.1 only (testing on one PC) |
| `--threads <n>` | Physics worker threads (default: automatic) |
| `--auto-start <n>` | Host: start when n players are in the lobby |
| `--exit-tick <t>` | Print the state hash after tick t and exit |
| `--bot` | Drive the local player with scripted input |
| `--shadow` | Run a shadow simulation and compare state hashes every tick |
| `--rewind-test` | Record inputs and snapshots, rewind and replay at the exit tick |
| `--replay <file>` | Watch a saved replay (`.rec`, the user folder's `replays/` keeps the latest matches, {doc}`../manual/multiplayer`) |
| `--bug-report-at <frame>` | Save a bug report at that frame, as if F9 was pressed (tests) |
| `--crash-at <frame>` | Crash on purpose at that frame to test crash reports (tests) |
| `--capture <png> [tick]` | Save a screenshot after the given tick (without a tick: the last frame of `--frames`) |
| `--frames <n>` | Draw n frames and exit (screens outside a match, such as the title) |
| `--ui-press <frame:node,...>` | Press the UI widget with that node name at that frame (screen flow tests, e.g. `20:start,50:solo`) |
| `--gpu-capture` | Load RenderDoc or PIX if installed; `F11` captures the next frame (development builds, {doc}`../manual/editor`) |
| `--gpu-capture-at <frame>` | Capture that frame without opening RenderDoc (tests) |
| `--system-info` | Print CPU and GPU features and exit (exit code 2 below the minimum spec) |
| `--benchmark [seconds]` | Benchmark mode: offline, fixed seed, bot input, vsync and sound off; measure for 30 seconds (or the given number) after a 3 second warm-up, write `benchmark.txt` and exit ({doc}`../manual/performance`) |
| `--benchmark-out <file>` | Path of the benchmark report (default `benchmark.txt`) |
| `--name <text>` | Player name in the lobby. Joining a running match again with the same name takes back the old slot |
| `--any-build` | Host: accept peers running a different build (compiler comparison tests) |
| `--net-lag <ms>`, `--net-jitter <ms>`, `--net-loss <%>` | Simulate a slow, uneven or lossy connection for this process: added round trip time, extra random delay per packet, share of packets dropped (testing) |
| `--hash-log <file>` | Write `<tick> <hash>` for every tick |
| `--desync-test <tick>` | Nudge one physics body before that tick to cause a desync (tests the desync dumps, {doc}`../manual/multiplayer`) |
| `--record-inputs <file>` | Save confirmed inputs and hashes (replay with `--headless --replay-inputs`) |
| `--mute` | Start with sound off (automated tests) |
| `--debug-ui` | Start with the debug UI shown (development builds, `F1` toggles it) |
| `--settings` | Start with the settings screen open |
| `--lang <code>` | Language of the game text (`assets/strings/<code>.txt`, default: `language` in `mealkit.project`) |
| `--headless` | Run without a window (the options below) |

## Headless (`<game>_headless.exe`, `<game>.exe --headless`)

| Option | Meaning |
|---|---|
| `--exit-tick <t>` | Run until tick t, print the state hash and exit (required unless replaying) |
| `--host [port]`, `--join <addr[:port]>`, `--local` | Networking, as in the game |
| `--players <n>`, `--auto-start <n>` | Maximum players; host starts when n players are in the lobby (default: `--players`) |
| `--match-data <n>` | Game-defined match value sent by the host (example: number of boxes, 0 = the scene's) |
| `--delay`, `--seed`, `--threads`, `--scene`, `--tuning`, `--shadow`, `--hash-log`, `--record-inputs`, `--any-build`, `--net-lag`, `--net-jitter`, `--net-loss` | As in the game |
| `--abort-host-at <t>` | The first player who took over as host exits at tick t without closing the session (host migration test) |
| `--replay-inputs <file>` | Replay a recorded match and compare every tick hash (no network) |

Window options (`--bot`, `--vsync`, `--fps`, `--size`, `--debug`, `--mute`, `--debug-ui`, `--settings`, `--lang`) are accepted and ignored.

## Editor (`MealKitEditor.exe`)

| Option | Meaning |
|---|---|
| (none) | Open the project manager |
| `--project <folder>` | Open a project |
| `[scene file]` | Open this scene |
| `--lang <ko\|en>` | Editor language for this run only (the saved setting is not changed; used for documentation screenshots) |
| `--frames <n>` | Exit after n frames |
| `--capture <png>` | Save a screenshot before exiting |
| `--view-mode <n>` | Start in a view mode: 1 wireframe, 2 normals, 3 LOD level, 4 overdraw, 5 over budget ({doc}`../manual/editor`) |
| `--gpu-capture` | Load RenderDoc or PIX if installed: View > GPU Capture and `F11` capture the next frame |
| `--play`, `--players <n>`, `--bot` | Start play mode, with several players and bot input |
| `--replay <file>` | Start by playing a saved replay or bug report zip (Scene > Open Replay...) |
| `--build-game` | Build the game code first |
| `--export` | Make a release build |
| `--upgrade` | Upgrade the project right away |
| `--project-settings` | Start with the Project Settings window open |
| `--tables`, `--sounds`, `--feedback` | Start with the Tables, Sounds or Feedback panel open |
| `--ui` | Start with the UI tab in front (the screen list; screens are edited in the MkUI Designer) |
| `--ui-check` | Compare the screens exported from Penpot with Penpot's layout boxes, print `UI-CHECK` lines and exit (exit code 2 on a difference; with `--lang` for the text language) |
| `--ui-render <ui/x.ui> <png>` | Draw one screen at half its board size, save it and exit (pixel comparison with the Penpot preview) |
| `--lookdev`, `--lookdev-model <model>` | Open the look dev window at start, showing that model (as if picked in Assets) ({doc}`../manual/editor`) |
| `--look-through <id>` | Look through that virtual camera at start |
| `--tool-path <folder>` | Also look for MealKit tools in this folder (repeatable; a tool you are building) ({doc}`../manual/tools`) |
| `--list-tools` | Print the tools the Tools menu finds and exit (no window) |
| `--bodies <n>`, `--debug` | As in the game |

For example: `MealKitEditor.exe --project . --frames 60 --capture out.png`. The scene editor's options are in {doc}`../manual/scene_editor`.

## Engine tools (`tools\`)

| Script | What it does |
|---|---|
| `new_project.ps1 -Name <name> [-Path <folder>] [-Template <template>] [-Modules <names>]` | Create a game project from a template (`arena` = the example game, the default; `empty`/`empty2d` = a floor, no menus) and add source modules (`screens,matchflow,camrig`) |
| `rename_project.ps1 -Project <folder> -Name <name>` | Rename a project (and its exe) |
| `upgrade_project.ps1 -Project <folder> [-Source]` | Upgrade a project to the current engine template (`-Source` replaces the game code with the example code, with a backup) |
| `check.ps1 [-Quick]` | Full check: builds, unit tests, determinism tests, captures |
| `mp_test.ps1 -Clients <n> -Ticks <t> [-Headless] [-Exe <path>] [-ClientExe <path>] [-Lag <ms>] [-Jitter <ms>] [-Loss <%>]` | Multiplayer determinism test (`-Lag`, `-Jitter`, `-Loss` pass the network simulation options to every peer) |
| `record_replay.ps1` | Remake the committed input recordings after an intended simulation change |
| `live_probe.ps1 [-Project <folder>] [-Kind game\|editor] [-Wait <s>] [-Events <n>] [-Topics stats]` | Find the running editor and game builds of a project, call `api/hello` and read state events ({doc}`tool_contract`) |
| `ci_test.ps1`, `ci_compare.ps1` | What CI runs for each build, and the comparison between builds |
| `check_platform.ps1`, `check_strings.ps1` | OS calls outside the platform layer; editor translations |
| `check_libs.ps1 [-Path <folder>]` | Runtime parts of MealKit tools in `third_party/` (the audio runtime), and a local checkout given with `-Path`, use no engine headers or macros |
| `update_mkaudio.ps1 -From <checkout> [-Ref <tag>]` | Copy a MkAudio tag into `third_party/mkaudio` and rebuild the notices ({doc}`../engine_dev/internals/audio`) |
| `check_layout.ps1 [-Project <folder>]` | Project folder layout and third-party metadata (also run by the release build and the editor) |
| `gen_notices.ps1 [-Check]` | Build `third_party/VERSIONS.txt` and `THIRD_PARTY_NOTICES.txt` from `third_party/<lib>/mealkit.txt` (`-Check` only compares) |
| `make_sample_models.py` | Regenerate the sample models |
| `make_sample_sounds.py` | Regenerate the sample sounds |
