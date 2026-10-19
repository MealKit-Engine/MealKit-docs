# Testing

## Full check

```powershell
powershell -ExecutionPolicy Bypass -File tools\check.ps1          # about 2 minutes, close the editor first
powershell -ExecutionPolicy Bypass -File tools\check.ps1 -Quick   # build + unit tests + determinism tests
```

Run the full check after changing the engine. Unit tests alone are `build\Release\bin\mealkit_tests.exe` (also in the Editor build; the `detmath-bits` hash must be the same in both builds).

The full check also tests the Vulkan graphics backend: it builds `VulkanEditor`, captures the same edit-mode view with the Direct3D 12 and the Vulkan editor, and compares them with `tools\compare_images.ps1` (at most 0.1 % of pixels may differ by more than 2 per channel, the status bar is left out). The edit-mode view is the same on every run; game screens change with time and are not compared.
A last Vulkan step plays a match with `--debug` and fails on any `[Vulkan]` validation message. Without the Vulkan SDK the validation layer is missing and the step shows `SKIP` (a skip does not fail the check).

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
