# Sim

This page explains the small tools that game simulation code (`sim/`) is built from: the object pool, the tick timer, tick events, confirmed commands and definition tables.
`sim` comes after `net` and `physics` in the layer order (see "엔진 폴더 사이 의존" in {engine}`docs/CODING_MODEL.md`). It is header-only, and game `sim/` code uses these tools instead of writing its own (rule 1 of "강제하는 방법" in {engine}`docs/CODING_MODEL.md`).
The code is in {engine}`engine/src/mealkit/sim`.

The engine has no `World` type. Each game declares its own `World` with a `WorldState` of `MEALKIT_FIELD`s and a `step()` that calls its systems in order. The tools on this page are the pieces that go into that state.

## Pool

`sim::Pool<T>` ({engine}`engine/src/mealkit/sim/Pool.h`) stores every object that appears and disappears during a match. Why all simulation objects come from a pool is in "생성과 파괴" in {engine}`docs/CODING_MODEL.md`.

### Ids with generations

An item is found by `sim::Id<T>`: a slot number and a generation number. Every slot has a generation that starts at 1 and goes up by one each time the slot is freed (it skips 0 when it wraps around).
`get(id)` returns the item only when the id's generation equals the slot's generation. An id kept after its object was destroyed therefore returns `nullptr`, even when the slot holds a new object. Generation 0 means an invalid id.

Looking up an object is one array access and one comparison, and an id is two plain numbers, so it can be stored in any state field and hashed.

### Fixed capacity

`init(capacity)` allocates everything once, when the match starts. After that the pool never allocates. When it is full, `create` returns an invalid id and `MEALKIT_ASSERT` fires. Every peer runs the same code, so every peer fails in the same way.

### Slot states and the end of a tick

Each slot is `Free`, `New`, `Alive` or `Dying`:

| Call | Effect |
|---|---|
| `create(value)` | Takes the next free slot and marks it `New`. The id works with `get` at once, so a projectile made this tick can be used this tick. |
| iteration `for (auto [id, item] : pool)` | Visits only `Alive` slots, in slot order. Objects made this tick are not visited until the next tick. |
| `destroy(id)` | Only marks the slot `Dying`. From then on `get` and iteration skip it. |
| `endTick(onDestroy)` | Called once at the end of `World::step()`. Sorts this tick's destroyed slots by slot number, calls `onDestroy(item)` for each (for example to destroy its physics body), frees them and raises their generation. Then all `New` slots become `Alive`. |

Because creating does not change what the current loop visits and destroying does not free a slot until the tick ends, systems can create and destroy objects while iterating. A slot is never reused within the same tick.

### Fixed order

Everything that decides order is the same on every peer:

- Iteration goes by slot number, not by creation time or memory address.
- Free slots are a stack. `init` fills it so that slot 0 is used first. Freed slots are pushed back in slot order, because `endTick` sorts them first, whatever order `destroy` was called in.
- `onDestroy` runs in slot order, so physics bodies are destroyed in the same order everywhere.

### Hash and snapshot

`hashState` adds the capacity, the count, every slot's generation and state, and the free list. The items' fields are added by the game through their field declarations, one by one, so struct padding never enters the hash.
`Pool` describes itself to the reflection system (`reflectOps`), so a `Pool` field in `WorldState` is hashed, saved in snapshots and shown in the editor's State panel without game code.
`T` must be trivially copyable, so an item holds no pointers to owned memory and can be copied as bytes.

## Tick timer

`sim::TickTimer` ({engine}`engine/src/mealkit/sim/TickTimer.h`) is "ready N ticks from now". It stores one number, `readyTick`:

- `start(now, ticks)` sets `readyTick = now + ticks`.
- `ready(now)` is `now >= readyTick`.
- `remaining(now)` is the ticks left, or 0.

It does not count down every tick and holds no float time. It is a `MEALKIT_STRUCT`, so a timer field in the state is hashed and saved by itself.
Durations come from data in seconds and are rounded to ticks once when loaded (the `Ticks` field type), so `sim/` code only sees whole ticks. See "시간이 걸리는 일" and "시간 값" in {engine}`docs/CODING_MODEL.md`.

## Tick events

`sim::TickEvents<T, N>` ({engine}`engine/src/mealkit/sim/TickEvents.h`) is how the simulation tells the view that something happened (a hit, an impact, a sound).
It is a fixed array of `N` items with a count:

- `sim/` code only writes: `world.events.push(event)`. It never reads the events.
- `World::step()` clears the array at the start of each tick.
- After every `step()`, the game session moves the events into a queue on the view side, so no event is lost when one frame runs several ticks.

Events are not part of the state hash, because the simulation never reads them. When the array is full, `push` asserts and drops the event, which only loses a visual effect.

## Commands

{engine}`engine/src/mealkit/sim/Commands.h` puts types on top of the confirmed command channel of `net::LockstepSession` (see {doc}`net`). Commands are for things that are not player input: cheats, input delay changes, votes.

- A command type is a `MEALKIT_STRUCT` that is trivially copyable (no strings, containers or pointers).
- `sim::sendCommand(session, command)` is called on the view side. It writes a 4-byte type id followed by the struct bytes. The type id is the FNV-1a hash of the type's declared name.
- `sim::forEachCommand(inputs, f)` is called at the start of `World::step()`. It gives each command with its player slot, in player order and then send order. `c.read(out)` copies the bytes when the type id and size match.

Commands are copied as bytes, so they mean the same only between the same builds. Lockstep already needs the same build. They go into input recordings, rewind and the shadow simulation together with the inputs. See "시뮬레이션에 넣는 입력 외 명령" in {engine}`docs/CODING_MODEL.md`.

## Table

`sim::Table<Row>` ({engine}`engine/src/mealkit/sim/Table.h`) holds a definition table in memory: row names (`ids`) and row values (`rows`), both in file order.
`sim/` code reads rows by number (`table[index]`, or `table.get(ref)` for a `RowRef`). `find(name)` searches by name and is meant for loading and the view side, not for code inside a tick.

A table is not part of `WorldState`. The game copies it into its `World` when the match starts, and its contents enter the content hash instead of the state hash. Reading table files is the job of {doc}`data`.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Generational indices (slot map) | `Pool`, `sim::Id` | A slot number plus a generation. Lookups are O(1), and a stale id is detected instead of reaching a reused slot. |
| Preallocated pool | `Pool::init` | All memory is taken at match start, so ticks never allocate. |
| Deferred destruction | `Pool::destroy`, `endTick` | Removal is a mark, and freeing happens once per tick, which makes create and destroy safe while iterating. |
| Deferred insertion into iteration | `Slot::New` | Objects made this tick wait one tick before loops visit them, so a loop never sees objects added during itself. |
| Deterministic free list | `m_free`, `sortSlots` | A stack of free slots refilled in slot order (insertion sort, since few slots die per tick). Slot reuse is the same on every peer. |
| Absolute-time timer | `TickTimer` | Stores the tick when it becomes ready instead of a countdown, so it needs no update and is one integer to hash. |
| Write-only event buffer | `TickEvents` | A fixed array cleared each tick. The simulation never reads it, so it stays out of the state hash. |
| Type tag by name hash | `commandType` | FNV-1a of the reflected type name identifies a command type without a central registry. |
| Field-by-field hashing | `Pool::hashState`, reflection | Only declared values enter the hash, never struct padding. |
