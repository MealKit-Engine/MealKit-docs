# Testing

## Full check

```powershell
powershell -ExecutionPolicy Bypass -File tools\check.ps1                     # everything, about 5 minutes; close the editor first
powershell -ExecutionPolicy Bypass -File tools\check.ps1 -Changed            # only the groups the changed files need; the default
powershell -ExecutionPolicy Bypass -File tools\check.ps1 -Quick              # build + unit tests + determinism tests
powershell -ExecutionPolicy Bypass -File tools\check.ps1 -Only render,editor # only these groups
```

The steps are sorted into groups: `static` (check scripts), `unit`, `det` (determinism and multiplayer), `game`, `tools`, `render` (reference images and Vulkan), `editor`, `project` and `export`. `-Changed` reads the git working tree (with `-Base <commit>` also the commits after it) and picks the groups from the changed paths with the rules at the top of `tools\check.ps1`. Documentation changes pick nothing, and an audio change does not run the multiplayer tests. `-DryRun` only prints the groups. Run the full check only when you want every group, for example before a release.

The determinism group always runs in the full check and with `-Only det`. Otherwise it runs only when the determinism key changed since its last pass: the simulation version of the Release build (a hash of the sources that reach the simulation) plus the tuning, scene, model, table and replay files. The key of the last pass is kept in `build\check-state\det.key`.

Unit tests alone are `build\Release\bin\mealkit_tests.exe` (also in the Editor build; the `detmath-bits` hash must be the same in both builds). `mealkit_tests.exe --only net,physics` runs only the tests of those areas, which are engine folder names (the first argument of `TEST_CASE(area, name)`); `-Changed` uses it for the changed engine folders.

The full check also tests the Vulkan graphics backend: it builds `VulkanEditor`, captures the same edit-mode view with the Direct3D 12 and the Vulkan editor, and compares them with `tools\compare_images.ps1` (at most 0.1 % of pixels may differ by more than 2 per channel, the status bar is left out). The edit-mode view is the same on every run; game screens change with time and are not compared.
A last Vulkan step plays a match with `--debug` and fails on any `[Vulkan]` validation message. Without the Vulkan SDK the validation layer is missing and the step shows `SKIP` (a skip does not fail the check).

## Graphics regression test

The full check draws a few fixed views without the editor UI and compares them with reference images in {engine}`engine/tests/golden`, so a shader change that breaks the picture fails the check before anyone looks.

- The views are listed in `engine/tests/golden/shots.txt`, one per line: name, scene (under `assets/`), camera position and yaw and pitch in degrees, and optionally a lighting model (`pbr`, `toon` or `unlit`; without it the project setting). Wind is drawn at screen time 0, so the pictures do not change between runs. `MealKitEditor --project . --render-golden <shots.txt> <folder>` draws each one for a few frames and saves `<name>.png`.
- Both the Direct3D 12 and the Vulkan editor are compared with the same images: at most 0.5 % of pixels may differ by more than 8 per channel. The limit allows small differences between GPUs and drivers.
- When an image differs, `build\check\golden\<name>-diff.png` (or `golden-vulkan`) shows the different pixels in red over a darkened reference.
- When you change the picture on purpose (a new shader feature, lighting), run `tools\check.ps1 -UpdateGolden`: it replaces the reference images with the Direct3D 12 ones, and the step shows `SKIP`. Look at the new images before committing them.
- When lighting models or post processing arrive, add views with them on and off.

## Performance baseline

- The `game` group runs `sandbox.exe --benchmark 10` (fixed seed, bots, vsync off) and compares average frame, 1 % worst frame, simulation per tick, GPU frame time and peak process/GPU memory with `engine/tests/perf/baseline.txt`.
- A value is flagged when it is more than the baseline's tolerance (20 %) over the baseline and also more than 0.5 ms (times) or 32 MB (memory) over it. The step then shows `WARN` with the values; it never fails the check, because other work on the PC easily slows a run down.
- The baseline belongs to one GPU (its `adapter` line). On a PC with another GPU the step shows `SKIP`, so CI machines and other developers' PCs do not compare against it.
- After a change that makes the engine faster or slower on purpose, run `tools\check.ps1 -UpdatePerf` on the measuring PC: it writes this run's numbers as the new baseline and shows `WARN: baseline updated`. Run it with nothing else busy, and commit the file. Each run's full report is `build\check\benchmark.txt`.

## Determinism test

```powershell
powershell -ExecutionPolicy Bypass -File tools\mp_test.ps1 -Clients 3 -Ticks 1800
```

This starts one host and N clients with bot input and checks that every peer produces the same state hash on the same tick.
Client i uses i physics threads, so it also checks that **the result does not depend on the thread count**.

```powershell
powershell -ExecutionPolicy Bypass -File tools\mp_test.ps1 -Clients 3 -Ticks 900 -ClientExe build\ClangCL\bin\sandbox.exe
```

This connects clang-cl clients to an MSVC host to see that **the result does not depend on the compiler** (swap with `-Exe` for the other direction).
Normally a different executable is refused, so for this test the host accepts other builds with `--any-build`.

`-Lag <ms> -Jitter <ms> -Loss <%>` gives every peer a slow, uneven and lossy connection (`--net-lag`, `--net-jitter`, `--net-loss`), so the resend paths run as they would over the internet. The result must still be identical; only the speed changes (when the round trip is longer than the input delay, the match waits for inputs).

With `-Headless`, every peer runs without a window (`--headless`). It runs as fast as inputs allow: 900 ticks take about 5 seconds (about 30 seconds with windows).

Inside one process: `sandbox.exe --bot --exit-tick 900 --shadow --rewind-test --vsync 0` must print `SHADOW ok` and `REWIND ok`.

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request. The result table appears in the summary of each Actions run.

| Build | Runner | What it builds |
|---|---|---|
| `windows-msvc` (reference) | windows-2022 | `build.bat` (Release) + `check_strings` and `check_platform` |
| `windows-clang-cl` | windows-2022 | `build.bat ClangCL` |
| `windows-msvc-editor` | windows-2022 | `build.bat Editor` (unit tests only) |
| `linux-x64-clang` | ubuntu-24.04 | headless: `sandbox_headless`, `mealkit_tests` |
| `macos-arm64-clang` | macos-15 (Apple Silicon) | headless: `sandbox_headless`, `mealkit_tests` |

- Every build runs `tools/ci_test.ps1`: unit tests (`detmath-bits`), a replay of the fixed input recordings `samples/*/replays/*.rec` with `--replay-inputs --hash-log` (`REPLAY ok`), and a headless `mp_test` (1+3, 900 ticks).
- The final `compare` job runs `tools/ci_compare.ps1`, which compares `detmath-bits` and the per-tick hash logs of every build with `windows-msvc`. When they differ, it shows the first tick that differs and fails.
- To run the same locally: `powershell -ExecutionPolicy Bypass -File tools\ci_test.ps1 -Bin build\Release\bin -Name windows-msvc`, then `tools\ci_compare.ps1 -Dir build\ci`.
  The Linux and macOS headless build is `cmake -S . -B build/Headless -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++` → `cmake --build build/Headless --target sandbox_headless mealkit_tests`.
- **When you change the simulation result on purpose** (physics, game rules, tuning, scenes, bot input), the recordings no longer match and CI and the "Committed replays" step of `check.ps1` fail.
  Run `build.bat`, then `powershell -ExecutionPolicy Bypass -File tools\record_replay.ps1` (4 headless players, seed 7, 900 ticks) to remake them, and commit them together. If it fails without such a change, it is a desync.
- `.rec` files are binary in `.gitattributes`, so line endings are never converted. The runners have no GPU, so screen captures and the shadow/rewind checks run only in the local `check.ps1`. Steam and EOS SDKs are absent, so the "none" backend is built.
