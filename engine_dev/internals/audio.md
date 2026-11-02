# Audio

This page explains how sound works inside: the sound event table, how a play request becomes a voice, how the engine chooses which voices are mixed, and how buses and 3D position work.
How to write sound events is in {doc}`../../manual/sound`. The code is in {engine}`engine/src/mealkit/audio`.

`audio` comes after `input` and before `ui` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"). `feedback` comes after it and plays sounds through it.
Sound is view side only: the simulation leaves tick events, and the view plays sounds for them. SimCheck blocks `audio/` headers in `sim/`. The design is in {engine}`docs/CODING_MODEL.md` ("How to play sounds").

## Runtime and glue

Sound has two layers, so the runtime lives in its own repository, shared with the MealKit audio tool ({engine}`docs/DECISIONS.md` 2026-10-26):

- **The runtime** `mkaudio::Mixer` from [MealKit Audio](https://github.com/MealKit-Engine/MealKit-Audio), vendored at a fixed version in {engine}`third_party/mkaudio`, does the mixing, buses, voices, containers, curves and subtitles described on this page. It is a library outside the engine: it includes no MealKit header and uses only miniaudio, stb_vorbis and the standard library. `tools\check_libs.ps1` fails the check if it uses an engine header or macro. Events come in as plain `mkaudio::EventDef` values through `setEvents`, clips as file paths, and log lines through a callback.
- **The glue** `audio::Engine` in {engine}`engine/src/mealkit/audio` keeps the game API. It reads `assets/sounds.events` with the runtime's `mkaudio::loadEventFile`, finds clip files with `findAsset`, writes the runtime's log lines to the engine log and adds the profiler zone. `Handle`, `Param` and the panel types are aliases of the runtime's types.

## miniaudio

The runtime is built on miniaudio. {engine}`third_party/mkaudio/src/MiniaudioConfig.h` sets it up, and {engine}`third_party/mkaudio/src/MiniaudioImpl.cpp` is the only file with the implementation:

- Decoders: WAV (sound effects, decoded into memory) and Ogg Vorbis through stb_vorbis (music, streamed from disk). MP3, FLAC, encoding and generators are compiled out.
- One device backend per platform: WASAPI on Windows. Other platforms will turn on their own backend in stage 5.

Why the engine uses miniaudio instead of SDL is in {engine}`docs/DECISIONS.md` (2026-10-18).

`Mixer::init` ({engine}`third_party/mkaudio/src/Mixer.cpp`) opens the default output device with one listener and **mixes in stereo**; miniaudio converts to the device's channel layout (7.1 and so on), so the mixing cost does not grow with the speaker count.
When there is no output device, `init` returns `false`, every later call does nothing, and the game runs without sound.

### Live service

`audio::addLiveService` adds the service `audio/` to the live connection of development game builds and the editor ({doc}`live`), for MealKit Audio:

| Request | What it does |
|---|---|
| `POST audio/play` | Body `event=<name>&p.<parameter>=<value>...`: plays the event at the listener's position (so 3D events are heard up close) |
| `POST audio/reload` | Reads the events file again now |
| `GET audio/state` | The file, the number of events, voice counts, the playing voices and the buses with their levels |

The service asks for the audio engine on each request, so it answers 503 when there is none (the editor before a project is open).

### Changing the runtime

Work on the runtime happens in a MealKit-Audio checkout, which has its own tests (mixing without a device, `Desc::noDevice` and `render`) and CI. To try a change in the engine before it is released, configure the engine with `-DMEALKIT_MKAUDIO_DIR=<checkout>`; CMake then builds the runtime from the checkout instead of `third_party/mkaudio`. When the change is tagged in MealKit-Audio, `tools\update_mkaudio.ps1 -From <checkout> -Ref <tag>` copies that tag into `third_party/mkaudio` (only `CMakeLists.txt`, `include/`, `src/` and the license, with the version in `mealkit.txt`) and rebuilds the notices.

## Sound events

A game plays an event name, never a file: `ctx.audio.play("hit", position, {{"speed", 6.0f}})`.
Events are `event` blocks of `assets/sounds.events`, read by the runtime's `mkaudio::parseEvents` ({engine}`third_party/mkaudio/include/mkaudio/Events.h`) into `mkaudio::EventDef`: clips, container, a parameter and its curve, random volume and pitch, distances, bus, loop, stream, priority, instance limit, steal rule, cooldown and subtitle. `mixbus` blocks become `BusDef` values (parent and mix volume) for `Mixer::setBuses`.

- The file is view-only, outside the content hash. Every 0.25 seconds `update` checks its write time and reads it again when it changed, so an edit is heard during play. MealKit Audio also asks for a reload at once after saving (below).
- If the project still has the old `assets/sounds.table`, the glue turns its `row` lines into `event` lines (the keys are the same), reads it and warns; `tools\upgrade_project.ps1` converts the file.
- On reload, each event keeps its last play time (for the cooldown) and its last clip. Playing sounds find their event again by name; a sound whose event was removed stops.
- Clips that are not streamed are decoded into memory when the events are read (`MA_SOUND_FLAG_DECODE`). Playing one makes a copy of the decoded sound (`ma_sound_init_copy`), so no disk read happens during play. Streamed clips are opened from the file each time they start.

## Voices

The engine has 256 voice slots. Each slot is a `Voice`: the event, its position and parameters, its state and up to 4 layers (miniaudio sounds).
A voice is **real** when miniaudio mixes it, or **virtual** when it only counts its play position. At most `maxVoices` voices are real; the default is 32, from the project setting `audioVoices`.

`play` and `play2D` only take a free slot and mark it pending. They return a `Handle` (slot index and generation number). When a sound ends, its slot's generation goes up, so an old handle stops working instead of controlling a new sound.
With no free slot the request is dropped (`voice limit`), and an unknown event name is dropped too (`missing event`).

Once per frame, `Engine::update` does three steps.

### 1. Starting pending requests

`startPending` sorts the pending requests by event, then by strength (the value of the event's curve parameter, or its volume). For each event:

1. While the cooldown runs, requests are dropped (`cooldown`).
2. When more requests for one event arrive in the same frame than `maxInstances`, only the strongest ones are kept (`same frame`). Ten hits in one frame do not play ten sounds.
3. When the event already has `maxInstances` voices, one is stolen: the oldest or the quietest, by the `steal` field. With `steal = none` the new request is dropped (`max instances`).
4. `start` picks a random volume and pitch inside the ranges and chooses the clip. A `switch` container rounds the parameter to a clip index. A `random` container never picks the clip it played last time (it draws from the other clips).

### 2. Choosing real voices

`manageVoices`:

1. Releases voices that finished or faded out.
2. Computes each voice's **audibility**: volume × curve volume × distance attenuation. Distance attenuation is linear: 1 inside `minDistance`, 0 beyond `maxDistance`.
3. Sorts voices by (priority + 1) × audibility, newest first on ties.
4. Walks the list. The first `maxVoices` voices with audibility of at least 0.002 are real: a new or returning voice is created in miniaudio, an existing one gets its new volume, pitch, position and filter.
5. Any other voice: a one-shot sound is dropped (`inaudible` or `voice limit`); a loop becomes virtual. Its play position is saved and its miniaudio sound is freed. A virtual voice advances its position by `dt × pitch` each frame, and when it becomes real again it continues from that position (modulo the clip length), so a far-away engine hum does not restart from the beginning.

### 3. Applying parameters

`apply` turns the event row into miniaudio values for each real voice:

- Volume = volume × random scale × lerp(`volumeAtMin`, `volumeAtMax`, t) × fade, where t is the parameter's position between `paramMin` and `paramMax`.
- Pitch the same way with the pitch fields (never below 0.01).
- With a low-pass curve, each layer runs through a second-order low-pass filter node. The cutoff is lerped the same way, and the filter is rebuilt only when the cutoff moves by more than 1 Hz.
- A `blend` container plays up to 4 clips together and crossfades neighbours by the parameter: layer i gets weight max(0, 1 − |t × (n − 1) − i|).

`stop(handle, fade)` fades the volume to 0 over the given time, then the voice is released.

Every dropped request is added to a list of the last 64 drops with its reason. The editor's Sounds panel shows that list, the voices (`voices()`) and the bus meters.

## Subtitles

An event with a `subtitle` string key adds a line to `subtitles()` when it is played: the key and the seconds left (`subtitleSeconds`). A second play of the same key only extends the time, so a burst of pushes is one line. `update` counts the lines down and removes them. The list does not depend on the volume, so the lines appear when the sound is muted. `game::Frontend` shows them (below).

## Buses

Buses are miniaudio sound groups. `master`, `music`, `sfx`, `ui` and `voice` are made at start; any other bus name in the table makes a new bus under `master`.

Each bus is wired as: bus group → FX node → master group → master FX node → device.
The FX node (next section) ends with a peak meter that keeps the peak, falling by 3 % per audio block, in an atomic value that the main thread reads; this is the only data the audio thread writes for the main thread.

`setBusVolume` sets a group's volume (the settings screen does this). `setMuted` sets the whole engine's volume to 0, for example when the window is in the background.

## Effects on buses

Each bus has one custom node after its group instead of a plain meter: bus group → FX node → parent group. The node runs on the audio thread and does, in order:

- a 2-pole low-pass (snapshots), skipped when no snapshot filters the bus;
- reverb, only on buses with `reverb true`: an own Freeverb (8 combs and 4 allpasses per channel, the public-domain algorithm) added on top of the dry sound. The main thread eases the values toward `setReverb`'s target and the node eases the amount across each block; when the amount reaches 0 the buffers are cleared so an old tail never returns;
- the peak meter.

The main thread writes the node's settings as atomics every update; the buffers are allocated on the main thread before reverb is switched on.
Bus volume is the player volume × mix volume × ducking × snapshot volume. Ducking follows the trigger bus: a bus counts as sounding when a mixed voice or a music track plays on it or on one of its children.

## Music

Music tracks are not voices: each track holds one streamed `ma_sound` per stem. `playMusic` finds the next beat or bar of the current track from its start frame and tempo (at least 50 ms ahead, since the audio thread mixes in blocks), schedules the new stems with `ma_sound_set_start_time_in_pcm_frames` plus a fade-in from that frame, and the old stems with `ma_sound_set_stop_time_with_fade_in_pcm_frames`. So the switch is exact to the sample no matter when the game calls it. Stems loop independently and stay together because they have the same length.
Each update moves every stem's weight toward its target from the stem parameter (a global parameter), and stopped tracks are freed a little after their end. Stingers are ordinary voices with a start frame on the music's grid.

## Occlusion and reverb zones

The runtime only takes numbers: `emitters()` lists the mixed 3D voices and `setOcclusion(handle, amount)` sets one (eased over 0.12 s into volume and low-pass, which uses the voice's low-pass node). The glue casts the rays: each update it checks up to 4 voices in turn with `PhysicsWorld::castRay` from the listener, stopping 1.5 m short of the sound so the body making it does not hide it. It reads the physics world between ticks on the main thread; the game exe and editor play pass `GameInstance::physics()` every frame, so audio never keeps a world from a finished match.
Reverb zones come from the scene's `reverb_zone` objects at match start. Each update the glue finds the smallest box around the listener (boxes may be rotated) and calls `setReverb` with its values and fade time when the zone changes.

## 3D sound

Every frame `game::Frontend` passes the camera position and forward direction to `setListener` ({engine}`engine/src/mealkit/game/Frontend.cpp`). Spatial voices get their position each time parameters are applied.
MealKit uses a left-handed coordinate system and miniaudio a right-handed one, so z is negated for the listener and every sound position.
miniaudio then does panning and attenuation (linear model with the event's minimum and maximum distance). The engine computes the same linear attenuation itself for audibility, so the choice of real voices matches what is heard.

Randomness here (volume, pitch, clip choice) uses the runtime's own small PCG32 generator seeded from the clock. It is view side only, so it does not need to be deterministic.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Event-based sound | `SoundEvent`, `Engine::play`, `mkaudio::EventDef` | Game code names an event; how it sounds is data in a table that sound designers edit. |
| Fixed slot pool with generations | `Voice`, `Handle` | 256 preallocated slots. A generation number per slot makes old handles harmless, like the simulation's pool ids. |
| Deferred start | `request`, `startPending` | Requests wait until the next update, so all requests of one frame are seen together before any starts. |
| Same-frame grouping | `startPending` | Sorts one frame's requests by strength and keeps only as many as the instance limit. |
| Voice stealing | `startPending` | When an event is at its limit, the oldest or quietest voice of that event is stopped for the new one. |
| No immediate repeat | `start` | Random containers draw from the clips other than the last one. |
| Virtual voices | `manageVoices` | Inaudible or over-limit loops stop mixing but keep counting their position, and resume in place. |
| Priority × audibility ranking | `manageVoices` | Chooses the voices to mix by importance times estimated loudness. |
| Linear distance attenuation | `estimate`, `ma_attenuation_model_linear` | Full volume inside the minimum distance, silent beyond the maximum. The same model is used for ranking and for mixing. |
| Parameter curves | `apply` | One parameter drives volume, pitch and low-pass cutoff by linear interpolation. |
| Crossfade blend container | `apply` | Triangle weights between neighbouring clips make a smooth blend along the parameter. |
| Audio graph with groups | `Impl::bus` | Buses are miniaudio sound groups chained to the master, so one volume change affects all sounds of a bus. |
| Peak meter with decay | `fxProcess` | The bus FX node tracks the peak level and lets it fall slowly, read through an atomic. |
| Freeverb | `Freeverb`, `fxProcess` | Parallel lowpass-feedback combs and series allpasses, stereo spread by a 23-sample offset. |
| Sample-exact scheduling | `playMusic`, `boundary` | Music switches and stingers are given absolute engine frames on the beat grid instead of starting on the next update. |
| Ducking and snapshots | `updateMix` | Bus gains move linearly toward targets each update; snapshot cutoffs interpolate in octaves. |
| Occlusion rays in turn | `Engine::Impl::occlusion` | A fixed number of rays per frame, rotated over the playing 3D voices, with eased results. |
| Decode once, copy to play | `decode`, `ma_sound_init_copy` | Effects are decoded when the table loads; each play shares the decoded data. |
| Streaming | `MA_SOUND_FLAG_STREAM` | Long music is read from disk while it plays instead of being decoded into memory. |
| Handedness conversion | `setListener`, `apply` | Negates z so miniaudio's right-handed space matches MealKit's left-handed one. |
| Library boundary | `third_party/mkaudio`, `tools\check_libs.ps1` | The runtime has its own repository, CMake project and include folder, and is checked for engine includes, so it builds and is used without MealKit. |
