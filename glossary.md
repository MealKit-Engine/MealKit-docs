# Glossary

Terms used in this documentation. The Korean translation uses the same words as the editor's Korean strings.

Content hash
: A hash of the data every peer must share: scene collision data, model files and tuning values. Peers with a different content hash are refused.

Controller
: What drives a pawn: a player or an AI.

Desync
: Peers whose simulations no longer match. Detected by comparing state hashes.

Deterministic simulation
: A simulation that gives bit-for-bit the same result from the same inputs on every PC, compiler and operating system.

Export (release build)
: Making the release folder `export/<game>/` that is given to players.

Game DLL
: The game code built for the editor (`<game>_game.dll`). The editor loads a copy and swaps it in when it changes (hot reload).

Headless
: Running only the simulation, without a window, renderer or audio.

Host
: The peer that relays inputs. The host is also a player.

Hot reload
: Swapping in newly built game code while the editor stays open.

Lockstep
: A network model where peers exchange only inputs and every peer runs the same simulation tick by tick.

Pawn
: A body inside the world. A controller possesses a pawn.

Platform layer
: The engine layer that holds all operating system calls (`mealkit/platform/`).

Player slot
: A person taking part in a match. Separate from the pawn they control.

Project
: A game project folder with a `mealkit.project` file.

RHI
: The engine's thin rendering hardware interface (`mealkit/rhi/`). Graphics APIs are called only behind it.

Rewind
: Going back to a recorded snapshot and running the recorded inputs again.

Shadow simulation
: A second copy of the world run in the same process to check that the simulation reads no hidden global state.

SimCheck
: The build-time checker for the determinism rules of the `sim/` folder.

State hash
: A hash of the simulation state, compared between peers every tick.

Tick
: One fixed step of the simulation (30 per second today).

Tuning
: Numbers the simulation reads (`assets/game.tuning`), edited in the editor's Tuning panel.
