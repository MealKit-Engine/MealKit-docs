# Sound and feedback

Sound and "game feel" (camera shake, screen flash, hit stop) are data. Sound designers change them without touching code, and the changes are heard at once, even during play.

## Sound events

Game code plays a **sound event** by name, never a file: `ctx.audio.play("hit", position, {{"speed", 9.0f}})`, or `ctx.audio.play2D("click")` for sounds with no position.
Events live in `assets/sounds.events`. Sound designers edit it in **MkAudio**, the audio tool of the MealKit family (below); it is also plain text that can be edited by hand:

```text
# MealKit audio events. Edit them in MkAudio or by hand
@format audio-events 2

mixbus ambience
parent music
volume 0.6

mixbus music
duckBy voice
duckVolume 0.35

event hit
clips sounds/hit_1.wav sounds/hit_2.wav sounds/hit_3.wav
param speed
paramMin 3
paramMax 15
volumeAtMin 0.2
```

An `event <name>` block is one event and a `mixbus <name>` block defines a bus; `music <name>` and `snapshot <name>` blocks are described below. Keys that are left out keep their defaults. The event keys are:

| Keys | Meaning |
|---|---|
| `clips`, `container` | Sound files (paths under `assets/`, separated by spaces). `random` picks one each time, `switch` picks by the parameter, `blend` crossfades by the parameter |
| `param`, `paramMin`, `paramMax` | The parameter that drives the container and the curves |
| `volume`, `pitch`, `volumeRandom`, `pitchRandom` | Base volume and pitch, and random variation each time |
| `volumeAtMin` ... `lowpassAtMax` | Curves: volume, pitch and low-pass filter at the start and end of the parameter range |
| `spatial`, `minDistance`, `maxDistance` | 3D position; full volume within the minimum distance, silent beyond the maximum |
| `bus` | Mix bus: `music`, `sfx`, `ui`, `voice`, or a bus defined with `mixbus` |
| `loop`, `stream` | Loop; stream from disk instead of loading into memory (music) |
| `priority`, `maxInstances`, `steal`, `cooldown` | Voice management (below) |
| `occlusionVolume`, `occlusionLowpass` | How a 3D sound is heard when something stands between it and the listener: volume multiplier and low-pass cutoff when fully blocked (defaults 0.35 and 1200 Hz) |
| `subtitle`, `subtitleSeconds` | A game string key shown at the bottom of the screen when the sound plays (players turn subtitles on or off in the settings), and for how long. Plays of the same key share one line. The screen is `assets/ui/subtitles.ui` |

A `mixbus` block sets a bus's `parent` (default `master`) and its mix `volume`, which is multiplied by the player's volume setting for that bus.
`reverb true` gives the bus reverb from reverb zones (below). `duckBy <bus>` lowers this bus while anything plays on the other bus or its children: down to `duckVolume`, in `duckAttack` seconds, and back in `duckRelease` seconds. Voice lines over music is the usual case.
The file is reloaded when it changes, also during play. The engine moves the listener with the camera.
Files written in format 1 (engine 0.7.12 and older) read as they are.
Projects made with engine 0.5.1 or older have `assets/sounds.table` instead; the engine still reads it with a warning, and `tools\upgrade_project.ps1` converts it to `sounds.events`.

### MkAudio

MkAudio is a separate program for sound designers ([MkAudio](https://github.com/MealKit-Engine/MkAudio), free, MIT). Open it from the editor's **Tools** menu once it is installed ({doc}`tools`), or start it with `MkAudio --project <project folder>`.

- **Events**: the list of events, with add, duplicate and delete. Events with a missing clip are red. Double-click an event to play it.
- **Event**: every setting of the selected event. Clips are picked from the `.wav` and `.ogg` files under `assets/`. The volume, pitch and low-pass curves are drawn over the parameter range; drag their end points. The 3D section draws the distance fade.
- **Buses**: the buses with their parent, mix volume and a level meter. The effects button of a bus turns on reverb and sets ducking.
- **Music**: the music tracks with their stems, tempo, transition and stem parameter. **Play** starts the track (switching on its transition point when another plays), the bar and beat are shown, a slider moves the stem parameter, and the stinger buttons play the selected event on the next beat or bar.
- **Mix**: snapshots, each with a **preview** box that turns it on in the preview, and reverb sliders to hear buses with reverb.
- **Preview**: plays the selected event through the same runtime the game uses, with sliders for the parameter, the distance and the occlusion.
- **Live**: the running development builds of the game and the editor for this project. **Play in game** plays the selected event in the game at the listener, and the game's voices and bus levels are shown.

Ctrl+S saves `assets/sounds.events`; a running game or editor reloads it at once. Ctrl+Z and Ctrl+Y undo and redo.

To notice when a sound changes by accident, run the golden render tests: `MkAudio --golden --project <project folder>` plays every event alone without a sound device and compares how loud it is over time with `tests/audio/<event>.golden`. The first run writes the files; commit them. Later runs print `GOLDEN ok` or `GOLDEN FAIL <event>` with the time and level that differ (within 1.5 dB counts as the same). After an intended change, `--update` rewrites the files.

### Music

A `music <name>` block is a track. Its `stems` are files of the same length that play together and loop. Game code starts a track with `ctx.audio.playMusic("arena")` and stops it with `ctx.audio.stopMusic(seconds)`.

```text
music arena
stems sounds/music_bass.wav sounds/music_drums.wav sounds/music_arp.wav
bpm 120
stemParam tension
```

| Keys | Meaning |
|---|---|
| `bpm`, `beatsPerBar`, `offset` | Tempo, time signature, and the seconds before the first beat (a pickup) |
| `transition` | Where `playMusic` switches to this track while another one plays: `bar` (default), `beat` or `immediate`. The switch lands on that exact sample |
| `crossfade` | Seconds the old track fades out and this one fades in at the switch |
| `stemParam`, `paramMin`, `paramMax`, `stemFade` | The first stem always plays; the others come in one after another as this game parameter rises from `paramMin` to `paramMax` (`ctx.audio.setGlobalParam("tension", 0.8f)`), each taking `stemFade` seconds |
| `volume`, `bus`, `loop` | Track volume, bus (default `music`), looping |

`ctx.audio.stinger("victory", audio::Quantize::Bar)` plays a sound event on the next beat or bar of the playing music (right away when none plays). `ctx.audio.music()` tells the playing track, the bar and the beat.

### Snapshots

A snapshot is a set of bus values that is turned on and off, for example a muffled mix while a pause menu is open:

```text
snapshot pause
fade 0.25
volume music 0.6
lowpass sfx 900
```

`volume <bus> <value>` multiplies a bus's volume and `lowpass <bus> <Hz>` filters it while the snapshot is on; `fade` is the time to turn it on or off. Game code calls `ctx.audio.setSnapshot("pause", true)`. When several are on, volumes multiply and the lowest cutoff wins.

### Walls and rooms

The engine muffles 3D sounds behind walls: every frame it checks a few of the playing 3D sounds with a physics ray from the listener, and a blocked sound eases to its event's `occlusionVolume` and `occlusionLowpass`. This needs the game to return its physics world from `GameInstance::physics()` (the sample does).
A **reverb zone** is a scene object (**Add > Reverb zone** in MkRender): a box with room size, damping, amount, width and a change time. While the listener is inside it (the smallest one when zones overlap), buses with `reverb true` get that reverb, and it fades back out when the listener leaves. Reverb zones are view only and outside the content hash, so players may differ in them.

### Voice management

The engine mixes at most `audioVoices` voices at once (Project Settings, default 32). Voices beyond that, and voices too far or too quiet to hear, become **virtual**: they keep counting their play position without being mixed, and come back when they are audible again.
Several plays of the same event in one frame are merged into one louder voice. An event can limit its own instances (`maxInstances`, with `steal`: `oldest`, `quietest` or `none`) and repeats (`cooldown`).
The simulation never plays sounds. It leaves tick events, and the view side turns them into sounds, so sound never affects the game state.
Physics impact sounds come from `PhysicsWorld::setContactEvents`; the contacts come in the same order whatever the number of physics threads.

### Sounds panel

Window > Data, Sounds page, and Window > Debug, Sounds page, in the MealKit editor shows the output buses with level meters and volume, the playing voices (mixed or virtual, audibility, distance), the most recently culled plays and why (cooldown, voice limit, missing clip ...), and a preview of the selected event. Events are edited in MkAudio.

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
| `effect` | A particle effect played at the event position (`assets/effects/<name>.fx`, the strength scales the particle count) |

**Hit stop freezes only the view.** The simulation keeps running in lockstep with the other players; when the stop ends, the view jumps back to the current state.

### Feedback panel

Window > Data, Feedback page, lists the game's event kinds and their rows. Edits are saved automatically and a playing game picks them up at once. **Preview** plays the rows of the selected kind right now, even while editing.

### Particle effects

A particle effect is a burst of glowing or soft particles, one file per effect: `assets/effects/<name>.fx`.
Open **Effects** at the bottom of the Feedback panel to choose an effect or make a new one, change its values (count, lifetime, direction and spread, speed, gravity, drag, size and color from start to end, softness, spin, additive) and press **Preview Effect** to play it at the camera focus.
The values are saved automatically. Put the effect name in a row's `effect` column to play it on that event. View code can also play one directly with `ctx.feedback.playEffect(name, position)`.
Particles are view side only and freeze during hit stop.
