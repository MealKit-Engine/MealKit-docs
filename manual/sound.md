# Sound and feedback

Sound and "game feel" (camera shake, screen flash, hit stop) are data. Sound designers change them in the editor without touching code, and the changes are heard at once, even during play.

## Sound events

Game code plays a **sound event** by name, never a file: `ctx.audio.play("hit", position, {{"speed", 9.0f}})`, or `ctx.audio.play2D("click")` for sounds with no position.
Events live in `assets/sounds.table`, a definition table edited in the Tables panel (or through CSV). Each row is one event:

| Columns | Meaning |
|---|---|
| `clips`, `container` | Sound files (paths under `assets/`, separated by spaces). `random` picks one each time, `switch` picks by the parameter, `blend` crossfades by the parameter |
| `param`, `paramMin`, `paramMax` | The parameter that drives the container and the curves |
| `volume`, `pitch`, `volumeRandom`, `pitchRandom` | Base volume and pitch, and random variation each time |
| `volumeAtMin` ... `lowpassAtMax` | Curves: volume, pitch and low-pass filter at the start and end of the parameter range |
| `spatial`, `minDistance`, `maxDistance` | 3D position; full volume within the minimum distance, silent beyond the maximum |
| `bus` | Mix bus: `music`, `sfx`, `ui`, `voice` |
| `loop`, `stream` | Loop; stream from disk instead of loading into memory (music) |
| `priority`, `maxInstances`, `steal`, `cooldown` | Voice management (below) |
| `subtitle`, `subtitleSeconds` | A game string key shown at the bottom of the screen when the sound plays (players turn subtitles on or off in the settings), and for how long. Plays of the same key share one line. The screen is `assets/ui/subtitles.ui` |

The table is reloaded when the file changes. The engine moves the listener with the camera.

### Voice management

The engine mixes at most `audioVoices` voices at once (Project Settings, default 32). Voices beyond that, and voices too far or too quiet to hear, become **virtual**: they keep counting their play position without being mixed, and come back when they are audible again.
Several plays of the same event in one frame are merged into one louder voice. An event can limit its own instances (`maxInstances`, with `steal`: `oldest`, `quietest` or `none`) and repeats (`cooldown`).
The simulation never plays sounds. It leaves tick events, and the view side turns them into sounds, so sound never affects the game state.
Physics impact sounds come from `PhysicsWorld::setContactEvents`; the contacts come in the same order whatever the number of physics threads.

### Sounds panel

View > Sounds shows the output buses with level meters and volume, the playing voices (mixed or virtual, audibility, distance), the most recently culled plays and why (cooldown, voice limit, missing clip ...), and a preview of the selected event.

## Feedback table

`assets/feedback.table` maps **tick events** to reactions. Game code passes every tick event to `ctx.feedback.trigger(event, localPlayer)` and does nothing else.
The event type is a `MEALKIT_STRUCT` whose first `MEALKIT_ENUM` field is the event kind. A row's id is the kind name (`Push`); more rows for the same kind take a suffix (`Push.local`).

| Columns | Meaning |
|---|---|
| `players` | Whose events: `any`, `local` (the player of this window) or `others` |
| `strengthFrom`, `strengthFull` | An event field that scales the reaction, and its value at full strength (empty is always full) |
| `positionFrom` | An event field holding the position (empty is everywhere) |
| `sound`, `soundParam` | A sound event to play, and a sound parameter set to the strength field |
| `shake`, `shakeSeconds`, `shakeFrequency`, `shakeRange` | Camera shake: size at full strength, time, speed, and the distance where it fades out |
| `flash`, `flashSeconds`, `flashColor` | Screen flash: strength, time and color |
| `hitStop` | Hit stop: the view freezes for this many seconds |

**Hit stop freezes only the view.** The simulation keeps running in lockstep with the other players; when the stop ends, the view jumps back to the current state.

### Feedback panel

View > Feedback lists the game's event kinds and their rows. Edits are saved automatically and a playing game picks them up at once. **Preview** plays the rows of the selected kind right now, even while editing.
