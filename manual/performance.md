# Performance

## Budget

The minimum spec is Intel 11th generation (Xe) integrated graphics at 1280×720 and 60 fps. Features that exceed the budget must be possible to turn off.

| Item | Budget |
|---|---|
| Whole frame (GPU) | 8 ms or less (half of a 60 fps frame stays free) |
| Simulation tick (30 Hz) | 4 ms or less per tick |
| Draw calls | 200 or fewer |
| Network (4 players, host sending) | 10 KB/s or less |
| Game executable | 5 MB or less (without assets) |

The current values are in the engine {engine}`roadmap <docs/ROADMAP.md>` ("Performance budget") and in {doc}`../about/introduction`.

## Reading the numbers

The engine collects its performance numbers in one place, `game::FrameStats` (`mealkit/game/FrameStats.h`), and averages them over a quarter of a second. During a match the window title shows them as one line:

```text
60 fps 16.67 ms (worst 18.2) | sim 0.42 ms/tick | tick 812 | P1 of 3 | rtt 34 ms | net 1.2/2.4 KB/s | 41 draws 2318 inst | audio 6+12 voices 0.08 ms | in sync
```

| Item | Meaning | Budget |
|---|---|---|
| `fps`, `ms`, `worst` | Average frame rate and frame time, and the longest frame in the period | 16.7 ms at 60 fps; a high `worst` is a hitch |
| `sim ms/tick` | CPU time of one `World::step()`, averaged | 4 ms |
| `tick` | The next tick to run | |
| `P1 of 3`, `rtt` | This player and the player count, round trip time to the host | |
| `net` | Kilobytes sent and received per second | 10 KB/s |
| `draws`, `inst` | Draw calls and drawn instances | 200 draw calls |
| `audio` | Playing and virtual voices, mixing time | |
| `in sync`, `DESYNC` | Whether the state hashes of all peers agreed | |

The same numbers appear in other places:

- **`F1` overlay** in development builds: one item per line ({doc}`debug_ui`).
- **Log**: a `perf: ...` line every two seconds in automated runs (`--exit-tick` or `--frames`), so a bot run leaves its numbers in the log.
- **Editor status bar**: the frame rate while editing; in play mode the players, tick, simulation time per tick, active physics bodies and sync state.

With vsync on, the frame rate stops at the monitor's rate and the frame time hides spare time. Measure with `--vsync 0` (or press `V` in the game).

## A heavier scene

To see how the simulation and drawing scale, the example accepts a box count that replaces the one in the scene:

```bat
build\Release\bin\sandbox.exe --bot --bodies 8000 --vsync 0 --exit-tick 900
```

`--bot` plays by itself and `--exit-tick` ends the run, so the `perf:` lines in the log can be compared between builds. The count is match data chosen by the host, so every peer uses the same value (`--match-data` in the headless game).

## Profiling (Tracy)

1. `build.bat Profile` → run `build\Profile\bin\sandbox.exe`.
2. Start the Tracy profiler (v0.14.1, https://github.com/wolfpld/tracy/releases) and connect to `127.0.0.1`.
3. You see CPU zones per frame (`Simulation`, `Physics step`, `Network`, `Render`, `Editor UI`) and the **GPU frame time**.

- In normal builds the `MEALKIT_ZONE("name")` markers produce no code at all, so add them to any function you want to measure.
- Profile builds collect data only while a profiler is connected (`TRACY_ON_DEMAND`) and accept connections only from 127.0.0.1.
- `MEALKIT_FRAME_MARK()` marks the end of a frame. Both macros are in `mealkit/core/Profile.h`.
