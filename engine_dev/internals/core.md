# Core

This page explains how the core folder works inside: the basic types, logging, time, math, deterministic math, random numbers, hashing and field declarations.
Core is the base of the engine. Together with `platform` it is the first group in the folder order, and the two may include each other; every other folder comes after them (see "엔진 폴더 사이 의존" in {engine}`docs/CODING_MODEL.md`).
The code is in {engine}`engine/src/mealkit/core`.

Core is small on purpose. Most of it is header-only, and only `Log.cpp` and `Reflect.cpp` have source files. Functions that need the operating system (the clock, file reading, the debugger) are declared here or in `platform/` and implemented in `platform/win32/` or `platform/posix/` (see {doc}`platform`).

## Types

{engine}`engine/src/mealkit/core/Types.h` gives short names for fixed-size types: `u8` to `u64`, `i8` to `i64`, `f32` and `f64`.
Engine and game code use these names, so sizes are the same on every compiler and platform. This matters for anything that is hashed, saved or sent over the network.

## Log

{engine}`engine/src/mealkit/core/Log.h` has three levels and four macros: `MEALKIT_INFO`, `MEALKIT_WARN`, `MEALKIT_ERROR` and `MEALKIT_FATAL`. They take a `printf` format.

Each line looks like `[  12.345][WARN ] message`: the time since the process started (`nowSeconds()`), the level, and the text.
Info lines go to standard output, warnings and errors to standard error, and every line also goes to the debugger output window (`debugOutput`).
A mutex keeps lines from different threads whole.

- `MEALKIT_FATAL` writes the line, shows an error dialog, and ends the process at once with exit code 1. Automatic tests turn the dialog off with `log::setDialogs(false)`.
- `MEALKIT_ASSERT(cond)` checks programmer mistakes. It exists in Debug and Editor builds (`MEALKIT_DEBUG` or `MEALKIT_ASSERTS`) and is removed from release builds. A failure writes an error line and stops in the debugger when one is attached.

The engine does not use exceptions. A failing function returns `false` or an empty `std::optional` and logs the reason where it failed ("실패 처리" in {engine}`docs/CODING_MODEL.md`).

## Clock

{engine}`engine/src/mealkit/core/Clock.h` declares three things. The implementations are in `platform/win32/Clock.cpp` and `platform/posix/Clock.cpp`.

| Function | Windows | Linux and macOS |
|---|---|---|
| `nowSeconds()` | `QueryPerformanceCounter`, counted from the first call | `clock_gettime(CLOCK_MONOTONIC)` |
| `sleepSeconds(s)` | a high-resolution waitable timer per thread (about 1 ms steps); `Sleep` if it cannot be made | `nanosleep` |
| `FrameLimiter` | sleeps with a high-resolution timer until 1 ms before the frame time, then spins for the last part | the same with `nanosleep` |

`FrameLimiter` limits the frame rate to save battery and heat on laptops. It keeps a target time for the next frame and adds one interval each frame.
When the program falls more than one interval behind (for example after a long load), it moves the target to now instead of rushing to catch up.

Wall-clock time is never used in the simulation. The simulation counts ticks; only the screen side uses `dt`.

## Math

{engine}`engine/src/mealkit/core/Math.h` has `Vec2`, `Vec3`, `Quat` and `Mat4` with the usual operations.

- Row vectors (`v * M`) and a left-handed system: x right, y up, z forward.
- Quaternion products follow Hamilton's rule: `a * b` applies `b` first, then `a`.
- `rotate(q, v)` uses the short form `v + w·t + u × t` with `t = 2 (u × v)`, which needs no matrix.
- `integrate(q, ω, dt)` turns an angular velocity into a new rotation with `q + ½ (ω, 0) q dt`, then normalizes. It uses no trigonometry, so the simulation may use it.
- `nlerp` interpolates rotations for drawing. It flips one quaternion when their dot product is negative, so it takes the short way around.
- `perspectiveReversedZ` puts the near plane at depth 1 and the far plane at 0. With a float depth buffer this spreads precision evenly over the distance.

Functions that call `std::sin`, `std::cos` or `std::tan` (`quatFromAxisAngle`, `perspectiveReversedZ`) are for drawing and input only. The simulation uses the versions in DetMath.

## DetMath

Lockstep needs every computer to get the same bits from the same simulation ("결정론 규칙" in {engine}`docs/CODING_MODEL.md`).
The basic IEEE 754 operations (`+ - * /` and `sqrt`) are required to be correctly rounded, so with `/fp:precise` (no FMA contraction) they give the same result on every CPU.
CRT functions such as `sin`, `cos`, `atan2`, `pow` and `exp` have no such rule: different CRT versions and CPUs may take different code paths and return different last bits. That is why they are banned in `sim/` and SimCheck reports them.

{engine}`engine/src/mealkit/core/DetMath.h` gives replacements built only from the basic operations, integer conversion and `std::sqrt`:

| Function | How it works |
|---|---|
| `detSin`, `detCos` | Range reduction: split `x` into a multiple `k` of π/2 and a remainder `r` with abs(r) ≤ π/4. π/2 is subtracted in two parts (`1.5703125` plus a small rest) so the remainder keeps its precision. The low two bits of `k` pick the quadrant, and a short polynomial computes sin or cos of `r`. |
| `detAtan`, `detAtan2` | For `x > tan(3π/8)` it uses `π/2 + atan(-1/x)`, for `x > tan(π/8)` it uses `π/4 + atan((x-1)/(x+1))`, so the polynomial only sees small values. `detAtan2` follows the CRT rules: the result is in [-π, π] and (0, 0) gives 0. |
| `detQuatFromAxisAngle`, `detYawQuat` | Rotation from an axis and angle with `detSin` and `detCos`. `detYawQuat(yaw)` turns around y; yaw 0 faces +z and a larger yaw turns toward +x. |

The polynomial coefficients are the minimax fits of the Cephes library (`sinf`, `cosf`, `atanf`).
Compared with the CRT, the error is about 6e-8 for sin and cos and 2.4e-7 for atan2 (for abs(x) ≤ 100 radians), and angles must stay below 2^14 radians.

The unit test `det_math` in {engine}`engine/tests/Tests.cpp` measures the worst error against the CRT and prints `detmath-bits <hash>`, a hash of every result bit. That hash must be the same in every build (Release, Editor, clang-cl) and on every CI platform.

## Random

`Pcg32` in {engine}`engine/src/mealkit/core/Random.h` is the only random number generator allowed in the simulation.

PCG32 keeps a 64-bit state and advances it with a linear congruential step (`state = state × 6364136223846793005 + inc`). The output is not the state itself: it shifts and XORs the old state down to 32 bits and then rotates them by an amount taken from the top 5 bits ("XSH RR").
It uses only integer operations, so the sequence is the same everywhere.

- `next01()` takes the top 24 bits and multiplies by 2^-24. A 24-bit integer fits a float exactly, so the result is deterministic and in [0, 1).
- `range(lo, hi)` and `below(n)` build on these.
- `Pcg32` is itself a `MEALKIT_STRUCT` with `state` and `inc` as fields. Put it in `WorldState` and the generator's state is hashed, saved in snapshots and shown in the State panel like any other field.

Do not take random numbers for effects from the simulation's generator: drawing would then change the simulation's sequence.

## Hash

{engine}`engine/src/mealkit/core/Hash.h` has the 64-bit FNV-1a hash: for each byte, XOR it into the value and multiply by the FNV prime.

- `fnv1a(text)` is `constexpr` and hashes a string. The engine uses it to make stable ids from type names (commands, loadouts) and, from the compile date and time, the build id that lockstep peers compare when they connect.
- `Hasher` hashes values one at a time. `add(v)` accepts only trivially copyable types.

The state hash that detects desyncs is built with `Hasher` field by field (`reflect::hashStruct`), never over a whole struct. Padding bytes between fields can hold any value, so hashing a struct's raw memory could give different hashes for equal states.

## Reflect

{engine}`engine/src/mealkit/core/Reflect.h` is the field declaration system. A struct declares its fields once, and the editor inspector, text files (`.scene` object fields, `.tuning`, `.table`, `mealkit.project`), the state hash, snapshots and the State panel all use that one declaration ("데이터와 설정" in {engine}`docs/CODING_MODEL.md`).

### Declaring

```cpp
MEALKIT_STRUCT(Tuning) {
    MEALKIT_FIELD(f32, playerSpeed, 7.0f, "Move speed");
    MEALKIT_FIELD(Ticks, respawn, Ticks::seconds(1.5f), "Respawn delay");
};
MEALKIT_ENUM(EventKind, u8, Push, Bounce, Spawn);
```

| Macro | What it declares |
|---|---|
| `MEALKIT_STRUCT(Name)` | A struct with declared fields. |
| `MEALKIT_OBJECT(Name)` | The same, and it is registered as a scene object kind (the editor's Add menu). `kObjectLabel` and `kObjectFlags` are optional. |
| `MEALKIT_VIEWMODEL(Name)` | The same, and it is registered as a view model for game screen UI. |
| `MEALKIT_FIELD(Type, name, default, label)` | A member with a default value and an editor label. |
| `MEALKIT_VIEW_FIELD`, `MEALKIT_FIELD_FLAGS` | A field with flags: `kFieldView` leaves it out of the content hash, `kFieldReadOnly` shows it without a widget. |
| `MEALKIT_ARRAY(Type, count, name, label)` | A `std::array` field. `MEALKIT_LIST` adds a count field next to it for UI lists. |
| `MEALKIT_ENUM(Name, Underlying, A, B, ...)` | An `enum class` whose value names appear in files and the editor. Values count up from 0. |
| `MEALKIT_TABLE(Row, path, flags)` | Registers a definition data table with a `MEALKIT_STRUCT` row type. |

Supported field types are `bool`, integers and enums, `f32`, `Vec3`, `Quat`, pool ids, `std::string`, `Ticks`, `Color`, `RowRef<Row>`, other declared structs, arrays and `sim::Pool<T>`. Any other type fails to compile with a message that points to `Reflect.h`.

### How the declaration becomes data

C++ has no reflection, so the macros build it from three small tricks:

1. `MEALKIT_STRUCT` reads `__COUNTER__` once and stores it in a function next to the struct. The struct also inherits from `Reflected<Name>`, which gives the fields a `MealkitSelf` type to refer to.
2. Each `MEALKIT_FIELD` declares the member and a static function `mealkitField(FieldSlot<N>)`, where `N` is `__COUNTER__` minus the struct's start. So the first field gets slot 0, the next slot 1, and so on. The function returns the member pointer, name, label and flags.
3. `forEachField<T>` calls `mealkitField(FieldSlot<0>)`, then slot 1, and stops at the first slot that does not exist (a `requires` check). This visits the fields in declaration order at compile time.

`typeOf<T>()` runs once per type (a function-local static). It creates one default instance, measures each field's offset from the member pointer, and fills a `TypeInfo`: the type name, label, size, flags, the list of `FieldInfo` (name, label, offset, flags, value description) and `create`/`destroy`/`copy` functions.
`valueOf<V>()` describes one value type as a `ValueInfo` with a `Kind` (Bool, Int, Float, Vec3, Struct, Array, Container, String, Ticks, Color, RowRef, ...).

Because the order of fields is the order of `__COUNTER__`, the declaration order is also the order of saving and hashing. No other macro that uses `__COUNTER__` may sit between field declarations.

The `create` and `destroy` functions are compiled into the module that defines the type. When the editor makes an instance of a game DLL type (`reflect::Instance`), the memory comes from and goes back to that module.

### Functions that use the description

All of these live in {engine}`engine/src/mealkit/core/Reflect.cpp` and walk a `TypeInfo` recursively. They work on any declared type without knowing it as a C++ type, which is how the editor edits game structs.

| Function | What it does |
|---|---|
| `hashStruct`, `hashOf` | Adds each field to a `Hasher`: scalars as their bytes, strings as length plus bytes, `RowRef` by its id, pools as slot bookkeeping plus each live item. Fields with flags in `skipFlags` are left out (the content hash skips `kFieldView`). |
| `saveStruct`, `loadStruct` | Binary snapshots with `ByteWriter` and `ByteReader`, field by field. They are only read back by the same build in the same process (rewind, shadow simulation), so there is no version header. |
| `toText`, `fromText`, `setFromText` | Text as `path value` lines. A path is a field name, `a.b` for nested structs and `a[2]` for arrays. Pools are not written as text. |
| `saveTextFile`, `loadTextFile` | Text files such as `.tuning`. `#` starts a comment. A key the type does not know, or a value that does not parse, is logged as a warning and skipped, so an old file still loads after fields are added or removed. Writing goes through `writeTextFile`, which replaces the file in one step. |
| `diffStruct` | Walks two values of the same type and lists the differing fields as `path: a -> b`, at most 32 lines. Pools also report slots that became alive or free, and differences only in their slot bookkeeping. The editor shows this when the shadow simulation diverges. |
| `resolvePath`, `formatScalar` | Find one value by path, and turn one value into text. |

Text formats of special values:

- Floats are written with `%.9g`, enough digits that reading the text gives back the exact same float.
- `Ticks` are whole ticks in memory and seconds in files. Reading rounds once with the project's tick rate (`reflect::setTickRate`, set when the project opens). Writing uses `%.6g` seconds, which reads back to the same tick.
- `Color` is RGBA8 in memory and `#RRGGBB` or `#RRGGBBAA` in files.
- Enums are written by name. Reading accepts the name or the number.
- `RowRef<Row>` is written as the row id. After loading, `data::resolveRows` fills in the row number that `sim/` reads.

Strings are allowed in settings, tuning and scene fields but not in simulation state: state is copied and hashed as bytes. `hasStringField<V>()` lets `game::Simulation` check this at compile time.

### Registration lists

`MEALKIT_OBJECT`, `MEALKIT_VIEWMODEL` and `MEALKIT_TABLE` add the type to a list in an `inline` variable initializer (`moduleObjectTypes()`, `moduleViewModels()`, `moduleTables()`). Each list belongs to the module (game exe or game DLL) that declares the types.
`mealkit.dll` never reads these lists itself; a game DLL hands them to the editor through `MEALKIT_GAME_MODULE` (see {doc}`editor`).

## Version

{engine}`engine/src/mealkit/core/Version.h` has `kEngineVersion` and `kDocsUrl`. CMake passes the version from the repository's `VERSION` file as `MEALKIT_VERSION`.
The editor compares it with `engineVersion` in a project's `mealkit.project` and offers `tools\upgrade_project.ps1` when they differ. Messages build documentation links from `kDocsUrl`, which points to the documentation of this engine version.

## Profile

{engine}`engine/src/mealkit/core/Profile.h` has two markers for the Tracy profiler: `MEALKIT_ZONE("name")` times the current scope and `MEALKIT_FRAME_MARK()` marks the end of a frame. Using them is described in {doc}`../../manual/performance`.

The markers always include the Tracy header, but only `build.bat Profile` (`MEALKIT_PROFILE=ON`) compiles the Tracy client and defines `TRACY_ENABLE`. In every other build the Tracy macros expand to nothing, so the markers cost nothing.
The profile build sets `TRACY_ON_DEMAND` (collect only while the profiler is connected) and `TRACY_ONLY_LOCALHOST` (accept connections only from 127.0.0.1, so no firewall prompt appears).

## Techniques used

The algorithms and patterns behind the parts above, with where to find them in the code.

### Determinism

| Technique | Where | What it does |
|---|---|---|
| Correctly rounded basic operations only | `DetMath.h`, `Math.h` | Simulation math uses `+ - * /` and `sqrt`, which IEEE 754 defines bit for bit, under `/fp:precise` with no FMA contraction. |
| Range reduction with split π/2 (Cody–Waite) | `detail::detReduce` | Subtracts `k·π/2` in two parts, a short exact part and a small rest, so the remainder keeps its precision for large angles. |
| Minimax polynomials | `detSinPoly`, `detCosPoly`, `detAtanPositive` | Short polynomials with Cephes coefficients approximate sin, cos and atan on a small interval, evaluated in Horner form. |
| Argument folding for atan | `detAtanPositive` | Uses atan(x) = π/2 + atan(-1/x) and atan(x) = π/4 + atan((x-1)/(x+1)) to keep the polynomial's input small. |
| Bit hash of results as a test | `det_math` in `Tests.cpp` | Hashes every result bit, so CI can compare builds and platforms with one number. |
| Trig-free rotation integration | `integrate` in `Math.h` | Integrates angular velocity with the quaternion derivative and normalizes, with no sin or cos. |
| Permuted congruential generator (PCG32) | `Pcg32` | A 64-bit LCG step plus an XOR-shift and a data-dependent rotation for output. Small, fast, integer only, and its state is a declared field. |
| Exact int-to-float for [0, 1) | `Pcg32::next01` | 24 random bits fit a float mantissa exactly, so no rounding differs between machines. |

### Hashing and data

| Technique | Where | What it does |
|---|---|---|
| FNV-1a | `fnv1a`, `Hasher` | XOR each byte into the hash, then multiply by the FNV prime. Simple and fast enough to hash the whole state every tick. |
| Field-by-field hashing | `reflect::hashStruct` | Hashes declared fields one at a time so struct padding never enters the hash. |
| Compile-time field list with `__COUNTER__` | `MEALKIT_FIELD`, `forEachField` | Each field gets a numbered static function; a recursive template visits the numbers in order until one is missing. |
| Run-time type description | `TypeInfo`, `ValueInfo`, `typeOf<T>()` | Built once per type from the compile-time list, with offsets measured on a default instance. Generic code then works through offsets and `Kind`. |
| Text serialization by path | `toText`, `fromText`, `loadTextFile` | `path value` lines keyed by field name, so files survive added, removed and reordered fields. Unknown keys become warnings. |
| Round-trip float text | `formatScalar` | `%.9g` is enough digits to read back the same `float`. |
| Binary snapshots | `saveStruct`, `loadStruct`, `ByteWriter`, `ByteReader` | Field-by-field binary copies for rewind and the shadow simulation. The reader checks bounds and reports a short buffer as failure. |
| Structural diff | `diffStruct` | Recursive comparison of two values of the same type that names each differing field by path. |
| Self-registration | `MEALKIT_OBJECT`, `MEALKIT_TABLE`, `MEALKIT_VIEWMODEL` | An `inline const bool` initializer adds the type to a per-module list before `main`, with no central list to edit. |

### Other

| Technique | Where | What it does |
|---|---|---|
| Hybrid sleep and spin | `FrameLimiter::wait` | Sleeps with a high-resolution timer until 1 ms before the target, then spins, for an even frame rate without burning a core. |
| Resynchronizing frame target | `FrameLimiter::wait` | When far behind, moves the target to now instead of running frames back to back. |
| Compiled-out markers | `Profile.h` | Tracy macros are empty unless `TRACY_ENABLE` is defined, so normal builds have no profiling cost. |
