# Cookbook

Short recipes for common tasks. Each game recipe is code from a reference sample (`samples/sandbox`, `samples/coop`) and keeps the simulation rules ({doc}`../manual/game_code`); the docs check fails when the sample code it shows changes.

```{toctree}
:maxdepth: 1

cooldowns
new_input
rounds
event_feedback
```

## Test multiplayer on one PC

1. Build the Release game: `build.bat`.
2. Start a host that listens only on this PC: `build\Release\bin\sandbox.exe --host --local`.
3. Start one or more clients: `build\Release\bin\sandbox.exe --join 127.0.0.1`.
4. Press Enter in the host's lobby to start the match.

To check automatically that all peers stay in sync, run the determinism test. It starts one host and N bot clients and compares the state hash of every peer:

```powershell
powershell -ExecutionPolicy Bypass -File tools\mp_test.ps1 -Clients 3 -Ticks 900
```

## Test multiplayer in the editor

Play mode can run several players at once. From the command line: `MealKitEditor.exe --project <folder> --play --players 3 --bot`.

## Check a scene without opening a window

Record a match headless and replay it to see that the result is the same:

```bat
sandbox_headless.exe --seed 7 --exit-tick 900 --record-inputs m.rec
sandbox.exe --headless --replay-inputs m.rec
```

The second command prints `REPLAY ok` when every tick matches.
