# Glossary

Terms used in this documentation. The Korean translation uses the same words as the editor's Korean strings.

Area object
: A scene object that is an invisible box (`kObjectArea`). Its position and size are the data, for example a spawn area.

Content hash
: A hash of the data every peer must share: scene collision data, model files, tuning values and simulation tables. Peers with a different content hash are refused.

Controller
: What drives a pawn: a player or an AI.

Desync
: Peers whose simulations no longer match. Detected by comparing state hashes.

Definition table
: Many rows of the same shape (weapons, items, enemy kinds) in `assets/tables/*.table`, edited in the editor's Tables panel.

Deterministic simulation
: A simulation that gives bit-for-bit the same result from the same inputs on every PC, compiler and operating system.

Feedback table
: `assets/feedback.table`: rows that turn tick events into sounds, camera shake, screen flash and hit stop. Edited in the editor's Feedback panel.

Export (release build)
: Making the release folder `export/<game>/` that is given to players.

Game DLL
: The game code built for the editor (`<game>_game.dll`). The editor loads a copy and swaps it in when it changes (hot reload).

Headless
: Running only the simulation, without a window, renderer or audio.

Host
: The peer that relays inputs. The host is also a player.

Input action
: A named control the game reads (`move`, `jump`) instead of keys. Bindings to keys, mouse and gamepad are in `assets/input.bindings`.

Hit stop
: A short freeze of the view on a strong hit. Only the view stops; the simulation keeps running.

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

Row reference
: A field (`RowRef<Row>`) that points at a row of a definition table by its id.

RHI
: The engine's thin rendering hardware interface (`mealkit/rhi/`). Graphics APIs are called only behind it.

Rewind
: Going back to a recorded snapshot and running the recorded inputs again.

Shadow simulation
: A second copy of the world run in the same process to check that the simulation reads no hidden global state.

Sound event
: A named sound in `assets/sounds.events`, edited in MealKit Audio (files, volume, pitch, 3D distance, bus, voice limits). Game code plays events by name, never files.

SimCheck
: The build-time checker for the determinism rules of the `sim/` folder.

State hash
: A hash of the simulation state, compared between peers every tick.

Tick
: One fixed step of the simulation (30 per second today).

Tuning
: Numbers the simulation reads (`assets/game.tuning`), edited in the editor's Tuning panel.

View tuning
: Numbers that are only seen, such as camera and colors (`assets/view.tuning`). Not in the content hash; changes apply at once.
