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

## Profiling (Tracy)

1. `build.bat Profile` → run `build\Profile\bin\sandbox.exe`.
2. Start the Tracy profiler (v0.14.1, https://github.com/wolfpld/tracy/releases) and connect to `127.0.0.1`.
3. You see CPU zones per frame (`Simulation`, `Physics step`, `Network`, `Render`, `Editor UI`) and the **GPU frame time**.

- In normal builds the `MEALKIT_ZONE("name")` markers produce no code at all, so add them to any function you want to measure.
- Profile builds collect data only while a profiler is connected (`TRACY_ON_DEMAND`) and accept connections only from 127.0.0.1.
- `MEALKIT_FRAME_MARK()` marks the end of a frame. Both macros are in `mealkit/core/Profile.h`.
