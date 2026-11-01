# Game code

This page shows how a game's code is put together, using the example game (`samples/sandbox` in the engine repository, `source/` in a project made from it).
The folders are described in {doc}`projects` ("Game code folders"), and the rules that keep multiplayer in sync in {doc}`multiplayer` ("Determinism rules").

## The three folders

| Folder | Runs | Reads | Writes |
|---|---|---|---|
| `sim/` | Once per confirmed tick, the same on every PC | Tick inputs, tuning, tables, the scene at match start | `WorldState`, the physics world, tick events |
| `view/` | Every frame, only on this PC | `WorldState` (two ticks, interpolated), tick events, view tuning, input actions | Camera, draw list, effects, the local input it sends |
| `app/` | Every frame | Everything | Connects the two: starts the match, runs ticks, hands events to the view |

The direction never reverses: `sim/` does not include `view/` or `app/` headers, never reads the camera, the frame time or the settings, and the view never changes the state.
When the view must change the simulation (a cheat button, a vote), it sends a **command** ({doc}`multiplayer`, "Commands").

## World and its state

The simulation is one `World` (`sim/World.h`). It holds the data fixed at match start (tuning, tables, spawn points, areas read from the scene), the **state** that changes every tick, the physics world and this tick's events.

```cpp
MEALKIT_STRUCT(WorldState) {
    MEALKIT_FIELD(u32, tick, 0, "Tick");
    MEALKIT_FIELD(mealkit::sim::MatchFlow, flow, {}, "Match flow");
    MEALKIT_ARRAY(PlayerSlot, mealkit::net::kMaxPlayers, slots, "Player slots");
    MEALKIT_FIELD(mealkit::sim::Pool<Pawn>, pawns, {}, "Pawns");
    MEALKIT_FIELD(mealkit::Pcg32, aiRng, {}, "AI random numbers");
    // ...
};
```

Everything that lives from one tick to the next is a `MEALKIT_FIELD` inside `WorldState`. The declarations are used three ways:

- **Hash**: `World::hash()` hashes every declared field (`reflect::hashStruct`) plus the physics state. Peers compare it to detect a desync.
- **Snapshot**: rewind, the shadow simulation and the editor's pause and step copy the declared fields.
- **State panel**: the editor shows the declared fields, with the label text, while playing.

A member that is not declared is missing from all three, so a desync caused by it cannot be seen. Values fixed for the whole match (tuning, tables, areas) stay as plain members of `World`.
State must be plain data: no pointers and no strings. Objects refer to each other with `Id<T>` (see below).

## One tick: World::step

`World::step(inputs)` calls the system functions **in a fixed order**. There is no per-object `Update`: every system is a free function that takes only `World&` (declared in `sim/Systems.h`), and when one system needs another it calls it directly.

```cpp
void World::step(const mealkit::net::TickInputs& tickInputs) {
    // copy this tick's 8-byte inputs into world.inputs, clear last tick's events
    applyCommands(*this, tickInputs); // commands first
    updateMatch(*this);               // countdown → playing → finished
    respawnPawns(*this);
    controlPawns(*this);              // inputs and AI → velocity, jump, push
    usePads(*this);
    physics.step(tickDt, 2);
    removeFallenPawns(*this);
    sensePawns(*this);                // physics result → state
    state.pawns.endTick([this](Pawn& p) { physics.destroy(p.body); });
    ++state.tick;
}
```

A new rule is usually a new system function in a new or existing `sim/` file, plus one line in `step()` at the place it belongs. `mealkit_add_game()` collects the files by pattern, so no CMake change is needed.

`World::reset()` starts a match: it reads the scene (static colliders, spawn points, the game's scene objects), sets the capacity of every pool, creates the controllers and pawns, and scatters the boxes. Bodies are always created in the same order (scene → pawns → boxes).

## Objects that come and go: Pool

Objects created and destroyed during a match (characters, projectiles, boxes) live in a `sim::Pool<T>` (`mealkit/sim/Pool.h`).

```cpp
state.pawns.init(controllers * 2);        // at match start: the capacity, never grows later
Id<Pawn> id = state.pawns.create(pawn);   // usable with get() at once
if (Pawn* p = state.pawns.get(id)) { ... } // nullptr once destroyed, even if the slot is reused
state.pawns.destroy(id);                  // only marks it
for (auto [id, pawn] : state.pawns) { ... } // slot order
state.pawns.endTick([&](Pawn& p) { physics.destroy(p.body); }); // last thing in step()
```

- Creating and destroying while iterating is safe: an object created this tick is not iterated until the next tick, and destroyed objects are removed by `endTick()` in slot order.
- An `Id<T>` carries a generation number, so an id kept after its object was destroyed returns `nullptr` instead of another object.
- When a pool is full, `create()` returns an invalid id on every peer alike (and asserts in development builds). Raise the capacity in `World::reset()`.

## "N ticks later": TickTimer

Cooldowns, respawn delays and countdowns are a `sim::TickTimer`: it stores the tick at which it becomes ready, not a decreasing float.

```cpp
MEALKIT_FIELD(TickTimer, pushReady, {}, "Next push");      // in a state struct
if (p.pushReady.ready(tick)) {
    p.pushReady.start(tick, world.tuning.pushCooldown);  // Ticks value from the tuning file (seconds there)
}
u32 left = flow.phaseEnd.remaining(tick);                // for a countdown display
```

## Match flow

Rounds, timers, teams and win conditions come from the engine's `mealkit::sim::MatchFlow` (`mealkit/sim/MatchFlow.h`). The flow goes waiting → countdown → playing → round end → (countdown for the next round) → results. The rules are tuning values: `minPlayers`, `countdown`, `roundLength`, `roundEndDelay`, `rounds` (best of N), `scoreLimit`, `lives` (elimination) and `teams` (side = slot number % teams; 0 is free for all). A round ends when a side reaches the score limit, when at most one side has players left (with lives), or when time runs out (highest score wins, a tie is a draw).

`sim/Match.cpp` calls `mealkit::sim::advanceMatch` once per tick with each player's round score and whether they are still in. It returns the transition made on that tick, and the game calls its own functions for it (`onRoundStart` resets scores and lives and puts everyone back at the spawn points). The scoreboard (`score`, `lives`, `falls`) lives in `PlayerSlot`. The screens only read `flow.phase`, `flow.round`, `flow.roundWinner` and `flow.matchWinner`.

Durations come from `Ticks` fields in the tuning, scene objects or tables ({doc}`assets`, "Time values"), so the code has no seconds or tick numbers in it.

## Players, controllers and pawns

The example splits a player from the body they move, so that respawning, spectating and AI need no special cases:

| Type | What it is | Lifetime |
|---|---|---|
| `PlayerSlot` | A person who joined (score, chosen body, team) | The whole match, `state.slots[player]` |
| `Controller` | Who drives a pawn: a player slot or an AI | The whole match, a pool |
| `Pawn` | The body in the world (movement mode, position, timers) | From spawn until it falls, a pool |

Change who drives what only with `possess(world, controller, pawn)` and `unpossess(world, controller)` (`sim/Pawns.cpp`), which keep both sides' ids in agreement.
A controller without a pawn is waiting to respawn. Read-only helpers for the view are `playerPawn(state, slot)` and `pawnPlayer(state, pawn)`.

## Physics

`world.physics` is a `physics::PhysicsWorld`. Game code never includes Jolt headers.

- Create bodies with `createBox`, `createCapsule` or `createConvexHull` and a `BodyDesc` (motion, mass, friction, locked rotation). Keep the returned `BodyId` in the state and destroy it in the pool's `endTick` callback.
- Move bodies by setting velocities (`setLinearVelocity`), not positions, and read the result back after `physics.step()` (`position`, `linearVelocity`, `castRay`). The example copies positions into `WorldState` in `sensePawns`, so the view never reads the physics world.
- `setContactEvents(minSpeed, maxPerTick)` makes `physics.contacts()` list strong impacts each tick, strongest first and independent of the thread count. The example turns them into `Impact` events for sounds.
- The result does not depend on the number of physics threads, and `World::hash()` includes the physics state (`physics.hashState`).

## Character movement modes

Pawns don't move their physics bodies themselves: each one has a `mealkit::sim::Mover` (`mealkit/sim/Movement.h`), and the body kind picks how it moves.

| Mode | How it moves | Good for |
|---|---|---|
| `Kinematic` | A swept capsule (Jolt CharacterVirtual): walks up steps, stops at steep slopes, sticks to the floor, rides moving platforms | Precise platforming and shooters |
| `Capsule` | A rigid capsule with locked rotation, steered by velocity | Shoving party games (the example's default) |
| `Floating` | A rigid capsule held above the ground by a spring | Physics interaction with smooth movement over bumps |
| `Ragdoll` | An active ragdoll: a hovering pelvis steers, motors swing the limbs in a walk, and `knockRagdoll` makes it go limp and get back up | Slapstick physics games |

- The mode is the `movement` column of `assets/tables/bodies.table` (in the example: `normal` Capsule, `light` Kinematic, `heavy` Floating, `ragdoll` Ragdoll), so players pick it with their body in the lobby.
- The numbers are `move.*` in the tuning: speed, accelerations, jump, and per mode the slope limit, step height and floor snap (Kinematic) or hover gap, spring and damping (Floating), or motor torque, stiffness, balance and stride (`ragdoll*`, Ragdoll).
- In the example, pushing knocks nearby ragdoll pawns down for `knockdown` seconds. The ragdoll's part positions are in `mover.ragdoll` for drawing.
- Each tick, `controlPawns` turns input or AI into a `MoveIntent` (direction and jump) and calls `move()`; after the physics step `sensePawns` calls `senseMover()` to read position, velocity and `mover.grounded`. Use `moverVelocity`/`setMoverVelocity` to launch a pawn (jump pads) in any mode.
- All modes are hashed, snapshotted and sent to late joiners, so switching modes needs no multiplayer work.

## From the simulation to the screen: tick events

The simulation tells the view what happened (a jump, a fall, a hit) through `world.events`, a `sim::TickEvents<GameEvent, N>`:

```cpp
world.events.push(makeEvent(EventKind::Jump, player, p.position, 0.0f)); // in sim/
```

`sim/` only writes events and never reads them, so they are not part of the state or the hash. `step()` clears them at the start of each tick.
The game declares its event type with `MEALKIT_STRUCT` and its kinds with `MEALKIT_ENUM` and names it as `EventType` in `GameSession`; the feedback table then picks sounds, shake and flashes by kind ({doc}`sound`, "Feedback table").

## Running the match: GameSession

`app/GameSession` implements `game::GameInstance`, the boundary between the engine and the game. The engine calls it the same way in the shipped exe, in editor play mode and in each player window:

| Call | When | The example |
|---|---|---|
| `lobby(session, options, userFolder)` | Every frame before a match | Sends the loadout (the chosen body) |
| `start(ctx, scene, options)` | Once when the match starts | `m_sim.start(...)` → `Headless::startWorld` → `World::reset` |
| `update(ctx, dt)` | Every frame | Screen flow, camera, local input, then `m_sim.update(...)` runs the confirmed ticks |
| `buildFrame(ctx, now, frame, out)` | Every frame | Camera and draw list from the two latest states |
| `stop(ctx)` | When the match ends | `m_sim.stop()` |
| `stateHash`, `stateView`, `setTuning`, `debug` | When the engine or editor asks | Forwarded to `World` and `game::Simulation` |

`game::Simulation<World>` (`mealkit/game/Simulation.h`) does the lockstep part: it runs only confirmed ticks, sends the local input for each, keeps the previous state for interpolation, and runs the shadow simulation, recording and rewind. The game gives it two callbacks:

```cpp
auto sample = [&](u32 tick) { /* build this tick's 8-byte input from ctx.actions and the camera */ };
auto onTick = [&](const World& world) {
    for (const GameEvent& e : world.events) ctx.feedback.trigger(e, session.localPlayer());
};
m_sim.update(session, dt, sample, onTick);
```

`onTick` runs after every tick, so no event is lost when one frame runs several ticks.

## Drawing: interpolation

Ticks run at a fixed rate (30 or 60 per second, `tickRate` in the project settings), and frames run as fast as the screen. The view draws between the last two states:

```cpp
const WorldState& previous = m_sim.previous();
const WorldState& current = m_sim.world().state;
const f32 alpha = m_sim.alpha(); // 0..1 between the two ticks
Vec3 at = lerp(before->position, pawn.position, alpha);
```

Find the same object in both states by its `Id<T>` (`previous.pawns.get(id)`); an object created this tick has no previous position, so draw it where it is.

An object can also **flash** white or **dissolve** (when its material has the dissolve feature, {doc}`assets`). Both are values from 0 to 1 in the instance flags, set by the view when it draws. Keep the time in the view, started from a tick event, never in `sim/`:

```cpp
// in onTick: a push event marks the pawns it hit (view/Draw.cpp onWorldEvent)
view.hitTime[id.slot] = viewTime;
// when drawing: fade the flash out over hitFlashSeconds (view tuning)
const f32 flash = pl.hitFlash * (1.0f - static_cast<f32>(viewTime - view.hitTime[id.slot]) / pl.hitFlashSeconds);
out.add(box, {pos, color.value, facing, pl.bodySize, render::instanceFlash(0, flash)});
```

`render::instanceDissolve(flags, progress)` works the same way (progress 1 is fully gone).

## Input

The tick input is 8 bytes per player (`net::kInputBytes`). The example packs it as a `GameInput`: a movement direction already turned into world space and quantized to `i8` by the view (so `sim/` needs no camera or trigonometry), and a byte of buttons.
`view/LocalInput` reads only input actions (`ctx.actions.axis2("move")`, `pressed("jump")`, see {doc}`input`), and keeps a press until the next tick is sampled so a short tap is never lost between ticks.

## Checking your changes

After changing `sim/`, check that it stays deterministic:

```bat
build\Release\bin\<name>.exe --bot --exit-tick 900 --shadow --rewind-test --vsync 0
```

It prints `SHADOW ok` (a second world with the same inputs got the same hash on every tick) and `REWIND ok` (rewinding and replaying reached the same state). Then run the multiplayer test from the engine folder:

```powershell
powershell -ExecutionPolicy Bypass -File tools\mp_test.ps1 -Exe <project>\build\Release\bin\<name>.exe -Clients 3 -Ticks 900
```

When the shadow check fails, it stops and logs the first tick that differs and the state fields that differ. The usual causes are a member that is not declared with `MEALKIT_FIELD`, a value left uninitialized, iteration over a hash map or pointers, or code reading something outside the simulation.
For a step-by-step example, see {doc}`../getting_started/first_gameplay`.

## Scenario tests: checking your rules

The checks above find determinism bugs. To check that a rule does what you meant ("pushing makes the opponent fall", "respawn 3 seconds after falling"), write a scenario in the project's `tests/` folder. It runs a match without a window and compares state values at given ticks:

```text
# The bot pushes the dummy off the arena
seed 7
inputs push.rec
tick 300 slots[1].falls == 1
tick 10s phase == Playing
tick 900 pawns[0].position.y > -5
```

- `seed` is the world seed (default 1). Without `inputs`, the solo bot plays (`Headless::botInput`); with `inputs`, the input recording next to the file is replayed (made with `--record-inputs`, or by the editor).
- `scene` picks a scene in `assets` (default: the start scene) and `ticks` how long to run (default: up to the last check, or the whole recording).
- `tick <n> <path> <op> <value>` checks the state after that tick. A tick ending in `s` is in seconds. Paths are `WorldState` fields as the [State] panel shows them: `a.b`, `array[2]`, `pool[slot]`.
- `==` and `!=` work on any value, written as in tuning files (enum names, `x y z`); `<`, `<=`, `>`, `>=` need numbers.

Run one with `build\Release\bin\<name>_headless.exe --test tests\push.scenario`. It prints `SCENARIO ok` or a `SCENARIO FAIL` line per failed check, and exits with code 6 on failure.
When you change the results on purpose, `--update-expected` rewrites the `==` values with the current results; review the diff before committing.

During solo play in the editor, **Save Scenario** in the play bar saves the inputs so far as `tests/scenarioN.rec` plus a `tests/scenarioN.scenario` with the current top-level state values. Keep the checks that state your rule and delete the rest. Solo play must keep replays (`keepReplays` in project settings).
