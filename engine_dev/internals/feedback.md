# Feedback

This page explains how the feedback table turns simulation events into sound, camera shake, screen flash and hit stop.
How to write the table is in {doc}`../../manual/sound` (section "Feedback table"). The code is in {engine}`engine/src/mealkit/feedback`.

`feedback` comes after `ui` and before `settings` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"). It plays sounds through `audio` and reads event values through reflection (`core`).
Everything here is view side. The simulation only pushes tick events; the view calls `ctx.feedback.trigger(event, localPlayer)` for each one, and the table decides what happens. The design is in {engine}`docs/CODING_MODEL.md` ("Attaching sound, effects, and shake to simulation events").

## The table

`assets/feedback.table` has one `feedback::Reaction` row per reaction ({engine}`engine/src/mealkit/feedback/Feedback.h`):

| Fields | Meaning |
|---|---|
| `players` | `any`, `local` or `others`: whose events this row reacts to |
| `strengthFrom`, `strengthFull` | An event field that gives the strength, and the field value that counts as full strength |
| `positionFrom` | An event field with the position (default `position`; empty means everywhere) |
| `sound`, `soundParam` | A sound event to play, and a sound parameter that gets the strength field's value |
| `shake`, `shakeSeconds`, `shakeFrequency`, `shakeRange` | Camera shake size at full strength (m), time, frequency and the distance where it fades out |
| `flash`, `flashSeconds`, `flashColor` | Screen flash amount at full strength, time and color |
| `hitStop` | Seconds the view freezes |

The table is view-only, outside the content hash. `Player::update` checks its write time every 0.25 seconds and reads it again when it changed, so an edit shows during play.

## Matching a row

An event is any `MEALKIT_STRUCT`. Its **kind** is the value name of its first `MEALKIT_ENUM` field, for example `Hit` or `Fall` (`kindName` in {engine}`engine/src/mealkit/feedback/Feedback.cpp`).
A row reacts when its id is the kind (`Fall`) or starts with the kind and a dot (`Fall.local`), so one kind can have several rows, for example one for the local player and one for everyone else.

For each matching row, `trigger`:

1. Checks `players`: it reads the event's `player` field and compares it with the local player number.
2. Reads the strength: the `strengthFrom` field divided by `strengthFull`, clamped to 0..1. Without the field the strength is 1.
3. Reads the position from `positionFrom` (a `Vec3` field). Without it, the reaction is not positioned.
4. Fires the reaction: plays the sound (3D when positioned, with `soundParam` set to the raw field value), adds a shake, adds a flash and extends the hit stop.

Event fields are found by name through reflection (`reflect::resolvePath`), so the table works with any event type the game declares, and the engine needs no code per game.

## Camera shake

Each shake keeps its start time, length, size, frequency, range, position and a phase. `cameraShake(focus)` adds up all active shakes:

- **Decay**: the size falls with (1 − t / length)², fast at first and gently at the end.
- **Distance**: a positioned shake is multiplied by 1 − distance / range from the camera's focus point, so far explosions shake less. A range of 0 means everywhere.
- **Shape**: x, y and z are sine waves at the shake frequency, 1.31 times and 0.87 times it, with different phase offsets. Mixing frequencies that are not multiples of each other gives an irregular tremble instead of a visible back-and-forth.
- Each new shake gets a different phase (1.7 radians more than the previous one), so two shakes started at once do not look the same.

The game's camera adds the offset to both its eye and its focus point, so the view moves without turning.

## Screen flash

Each flash fades linearly over its time. `screenTint` returns the strongest active flash.
The flash color is turned into linear color by squaring, the same gamma 2.0 approximation as the shader. `game::Frontend` writes it into `FrameParams::tintColor` and `tintAmount` after the game builds its frame, and the renderer mixes the whole picture and the clear color toward it (see {doc}`render`).

## Hit stop

`hitStop()` is true until the latest hit stop ends. While it is true, the game's view stops its own clock, interpolation and effects.
**The simulation does not stop.** Lockstep peers must keep running the same ticks, so a pause in the simulation would desync. Only the picture freezes for a moment.

`setAccessibility(shake, flash, hitStop)` comes from the player settings (the settings service calls it): the shake offset and the flash amount are multiplied by 0..1, and `hitStop()` stays false when hit stop is off. The table itself is not changed.

## Editor support

- `preview(kind, position)` fires a row at full strength, for the preview in the editor's Feedback panel.
- `reload()` reads the table at once after the editor saves it, and `clear()` removes running shakes, flashes and hit stop when play stops.
- `rowIds()` lists the rows for the panel.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Data-driven reactions | `assets/feedback.table` | What an event looks and sounds like is data, edited during play without code changes. |
| Reflection-based field lookup | `readFloat`, `readVec3`, `kindName` | Reads the kind, player, strength and position from any event type by field name. |
| Row id prefix matching | `Player::trigger` | `Kind` and `Kind.suffix` rows let one event kind have several reactions. |
| Strength normalization | `trigger` | Divides an event field by a full-strength value and clamps it, so one row scales from light to heavy hits. |
| Quadratic decay | `cameraShake` | (1 − t / length)² gives a strong start and a soft end. |
| Sum of incommensurate sines | `cameraShake` | Three sine waves at unrelated frequency ratios make an irregular shake without random numbers. |
| Linear distance falloff | `cameraShake` | Fades positioned shakes with distance from the camera's focus. |
| Strongest wins | `screenTint` | Overlapping flashes do not add up to a white screen. |
| View-only time freeze | `hitStop` | Freezes the presentation while the deterministic simulation keeps running. |
