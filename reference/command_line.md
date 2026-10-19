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
| `--delay <ticks>` | Input delay in 33 ms ticks (default 3) |
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
| `--capture <png> [tick]` | Save a screenshot after the given tick (without a tick: the last frame of `--frames`) |
| `--frames <n>` | Draw n frames and exit (screens outside a match, such as the title) |
| `--ui-press <frame:node,...>` | Press the UI widget with that node name at that frame (screen flow tests, e.g. `20:start,50:solo`) |
| `--system-info` | Print CPU and GPU features and exit (exit code 2 below the minimum spec) |
| `--any-build` | Host: accept peers running a different build (compiler comparison tests) |
| `--hash-log <file>` | Write `<tick> <hash>` for every tick |
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
| `--delay`, `--seed`, `--threads`, `--scene`, `--tuning`, `--shadow`, `--hash-log`, `--record-inputs`, `--any-build` | As in the game |
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
| `--select <i>` | Select object i |
| `--play`, `--players <n>`, `--bot` | Start play mode, with several players and bot input |
| `--build-game` | Build the game code first |
| `--export` | Make a release build |
| `--upgrade` | Upgrade the project right away |
| `--project-settings` | Start with the Project Settings window open |
| `--tables`, `--sounds`, `--feedback` | Start with the Tables, Sounds or Feedback panel open |
| `--ui <file.ui>` | Start with the UI panel previewing this screen |
| `--bodies <n>`, `--debug` | As in the game |

For example: `MealKitEditor.exe --project . --frames 60 --select 5 --capture out.png`.

## Engine tools (`tools\`)

| Script | What it does |
|---|---|
| `new_project.ps1 -Name <name> [-Path <folder>]` | Create a game project from the template |
| `rename_project.ps1 -Project <folder> -Name <name>` | Rename a project (and its exe) |
| `upgrade_project.ps1 -Project <folder> [-Source]` | Upgrade a project to the current engine template (`-Source` replaces the game code with the example code, with a backup) |
| `check.ps1 [-Quick]` | Full check: builds, unit tests, determinism tests, captures |
| `mp_test.ps1 -Clients <n> -Ticks <t> [-Headless] [-Exe <path>] [-ClientExe <path>]` | Multiplayer determinism test |
| `record_replay.ps1` | Remake the committed input recordings after an intended simulation change |
| `ci_test.ps1`, `ci_compare.ps1` | What CI runs for each build, and the comparison between builds |
| `check_platform.ps1`, `check_strings.ps1` | OS calls outside the platform layer; editor translations |
| `check_layout.ps1 [-Project <folder>]` | Project folder layout and third-party metadata (also run by the release build and the editor) |
| `gen_notices.ps1 [-Check]` | Build `third_party/VERSIONS.txt` and `THIRD_PARTY_NOTICES.txt` from `third_party/<lib>/mealkit.txt` (`-Check` only compares) |
| `make_sample_models.py` | Regenerate the sample models |
| `make_sample_sounds.py` | Regenerate the sample sounds |
