# Physics

This page explains how the physics layer works inside: a small wrapper around Jolt Physics, and what it does to give the same result on every PC.
`physics` comes after `net` in the layer order and includes only `core` (see "Dependencies between engine folders" in {engine}`docs/CODING_MODEL.md`).
The determinism rules that game code follows are in {doc}`../../manual/multiplayer`. The code is in {engine}`engine/src/mealkit/physics`.

## The wrapper

`physics::PhysicsWorld` ({engine}`engine/src/mealkit/physics/PhysicsWorld.h`) is the only physics API that game code sees. Bodies are plain `BodyId` numbers (`u32`), and no Jolt header reaches game code: the engine links Jolt privately.
This keeps Jolt types out of the simulation state, so a `BodyId` can be a `MEALKIT_FIELD` that is hashed and saved like any other number.

| Function | What it does |
|---|---|
| `init(maxBodies, threads)` | Creates the Jolt physics system and a job thread pool. `threads = 0` uses the core count minus one (for the main thread), between 1 and 6. |
| `createBox` / `createSphere` / `createCapsule` / `createConvexHull` | Creates a static, dynamic or kinematic body from a `BodyDesc` (friction, restitution, damping, mass, rotation lock, sleep). |
| `destroy` | Removes a body. |
| `optimize` | Rebuilds the broad phase once after the static bodies are made. |
| `step(dt, collisionSteps)` | Advances the world. |
| `castRay` | Finds the nearest body on a ray, optionally ignoring one body. |
| `hashState` | Adds every body's id, position, rotation and velocities to the state hash, in creation order. |
| `save` / `restore` | Snapshots the whole physics state (see below). |

There are two collision layers: static bodies (`NonMoving`) and everything else (`Moving`). Two static bodies never collide with each other.
A mass of 0 means Jolt computes it from the shape with a density of 1000 kg/m³. With `lockRotation`, only the three translation axes are free, so a character does not fall over.

## Determinism

Lockstep needs every peer to compute bit for bit the same physics. Jolt supports this when it is built for it and called in the same order. The rules are in "Determinism rules" in {engine}`docs/CODING_MODEL.md`.

### Build options

Jolt is built from source with fixed options in {engine}`cmake/MealKit.cmake`:

- `CROSS_PLATFORM_DETERMINISTIC` is on. Jolt then avoids operations whose result can differ between compilers and CPUs.
- AVX, AVX2, AVX-512, FMA (`USE_FMADD`), F16C, LZCNT and TZCNT are off. SSE4.1 and SSE4.2 are on.
  The same executable then runs the same instructions on every CPU, including office Pentium and Celeron CPUs. A fused multiply-add rounds once instead of twice, so allowing it on some CPUs would change results.
- Floating point exceptions are off, and the Jolt GPU compute back ends are off.
- With clang-cl, Jolt also gets `-ffp-contract=off`, so the compiler does not fuse a multiply and an add by itself. MSVC uses `/fp:precise`.

These options are not to be changed (engine `CLAUDE.md`).

### Same calls in the same order

Jolt gives the same result for the same sequence of calls. Game code therefore creates and destroys bodies and applies forces in the same order on every peer, which the fixed system order of `World::step()` and the slot order of `Pool<T>` already give (see {doc}`sim`).

Body ids are chosen by the engine, not by Jolt. `PhysicsWorld` keeps its own id allocator: a list of free index numbers and a sequence number per index. Destroying a body increments the sequence number of its index and puts the index back on the free list, so a reused index gives a different id. Because this allocator is part of the snapshot, bodies made after a restore get the same ids as the first time.

### Thread count does not matter

Jolt's job system splits the work across threads, but its results do not depend on how many threads there are. A peer with 2 cores and a peer with 8 cores compute the same state.
The shadow simulation uses this: it runs its second world with 1 physics thread and still must match the real world's hash every tick.

### Steps per tick

`step(dt, collisionSteps)` passes `collisionSteps` to Jolt, which splits the time step into that many collision steps. The sandbox sample calls `physics.step(kTickDt, 2)`, so a 30 Hz tick runs two physics steps for better stability ({engine}`samples/sandbox/sim/World.cpp`). The number is an algorithm constant in game code, the same on every peer.

### Contact events

`setContactEvents(minSpeed, maxPerStep)` turns on events for pairs that newly touch at a speed of at least `minSpeed` (the closing speed along the contact normal). They are for sound and effects, not for game rules, so they are not in the state hash. With `minSpeed = 0` (the default) no listener is installed and they cost nothing.

Jolt reports contacts from its worker threads, in an order that depends on thread timing. The collector stores them under a lock, and at the end of `step()` sorts them by speed (strongest first), then body ids, then contact position, and keeps the first `maxPerStep`.
After sorting, the list is the same for any thread count, so a game can turn contacts into tick events without breaking determinism.

### Convex hulls from original vertices

A solid with a model gets a convex hull shape. Its points come from `asset::Model::hullPoints`, which {engine}`engine/src/mealkit/asset/ModelCache.cpp` takes from the vertices as read from the glTF file, **before** meshoptimizer changes the mesh (at most 1024 points, taking every n-th vertex).
The physics shape therefore never depends on the optimizer's output, which could change with a library version.
If Jolt cannot build a hull from the points, `createConvexHull` logs a warning and makes a box from their bounds instead.

## Snapshots

`save` fills a `PhysicsSnapshot` with three things: the list of bodies with their shapes and settings, the id allocator, and Jolt's full state written by `PhysicsSystem::SaveState` through a byte-array `StateRecorder`.

`restore` first makes the set of bodies match the snapshot: bodies created after the snapshot are removed, and bodies destroyed after it are created again **with the same ids** (Jolt's `CreateBodyWithID`). Then Jolt reads the saved state back.
Snapshots are used only inside one process, for the rewind checkpoints and the shadow simulation (see {doc}`editor`).

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Opaque handle API (facade) | `PhysicsWorld`, `BodyId` | Game code uses numbers and engine math types only. Jolt stays a private dependency. |
| Cross-platform deterministic floating point | {engine}`cmake/MealKit.cmake` | Fixed instruction set (SSE4.2, no AVX or FMA), no floating point contraction, Jolt's deterministic mode. |
| Two broad phase layers | `BroadPhaseLayerMap`, `ObjectPairFilter` | Static and moving bodies live in separate trees. Static pairs are never tested. |
| Generational ids with a fixed free list | `BodyIdAllocator`, `destroy` | A reused index gets a new sequence number, and reuse order is fixed, so ids are the same on every peer and after a restore. |
| Sorting events gathered in parallel | `PhysicsWorld::step` | Contacts from worker threads are sorted by a full key (speed, ids, position) to remove the thread-timing order. |
| Hashing in creation order | `hashState` | Walks the body list in creation order, not Jolt's internal order, and adds each value field by field. |
| State recording | `save`, `restore`, `ByteStateRecorder` | Jolt's own state serialization into a byte array, plus the engine's body list so created and destroyed bodies come back with the same ids. |
| Convex hull with a fallback | `createConvexHull` | Jolt builds the hull. Degenerate point sets (for example all on one plane) fall back to an axis-aligned box from the point bounds. |
| Sub-stepping | `step(dt, collisionSteps)` | Several collision steps per tick reduce tunneling and jitter at a 30 Hz tick rate. |
