# Tool contract

What a MealKit tool (a separate program, such as the audio tool) can rely on, so it works with the engine without sharing its code. The contract has four parts: the project folder, the text formats, the live connection and the tool manifest.
Tools for users are described in {doc}`../manual/tools`; the decisions behind this page are in {engine}`docs/DECISIONS.md` (2026-10-26) and {engine}`docs/CODING_MODEL.md`.

## Project folder

A project is the folder that holds `mealkit.project`. A tool is started with `--project "<folder>"`; started by hand, it can walk up from a file until it finds `mealkit.project`, like the Blender add-on.

- A tool's own source files go in `art/<tool>/` (kept in git, not shipped).
- What the game loads goes in the fixed kind folders of `assets/` ({doc}`../manual/projects`). `tools\check_layout.ps1` fails on files in the wrong place.
- `build/` is generated and not in git; the live connection writes there.

## Text formats

Every MealKit text format is line-based UTF-8 that merges in git, and has a **format line** right after its comment header:

```text
# MealKit table (SoundEvent). Edit it in the editor's [Tables] panel or import a CSV there.
@format table 1

row hit
...
```

`@format <kind> <version>`. The kinds are:

| Kind | Files |
|---|---|
| `project` | `mealkit.project` |
| `tuning` | `assets/game.tuning`, `assets/view.tuning` |
| `settings` | the player's `settings.ini` |
| `table` | `assets/tables/*.table`, `assets/input.bindings`, `assets/feedback.table` |
| `scene` | `assets/scenes/*.scene` (version 2) |
| `ui` | `assets/ui/*.ui` |
| `strings` | `assets/strings/<language>.txt` |
| `tool` | `mealkit-tool.txt` (below) |
| `audio-events` | `assets/sounds.events` (defined by the audio runtime, edited in MealKit Audio, {doc}`../manual/sound`) |

Rules for readers and writers:

- A file without the line is version 1.
- A reader warns about another kind or a newer version than it knows, and reads the keys it knows.
- A writer always writes the newest version. A format change raises the version, and readers get a migration for older versions.
- A tool's own formats follow the same rules with their own kind.

The engine's code for this is {engine}`engine/src/mealkit/core/TextFormat.h`.

## Live connection

The editor and development game builds run a small HTTP server on `127.0.0.1` ({engine}`engine/src/mealkit/live/Server.h`). Release builds do not.

### Finding a running editor or game

Each running instance writes `<project>/build/live/<kind>-<pid>.json` and deletes it when it closes:

```json
{"protocol":1,"kind":"game","pid":8712,"port":51543,"token":"8f3c...","project":"sandbox","engine":"0.5.1",
 "url":"http://127.0.0.1:51543/8f3c.../"}
```

`kind` is `editor` or `game` (several game windows each have a file). A file can be left over after a crash: treat an instance that does not answer `api/hello` as gone. The next server to start removes files of processes that no longer exist.

### Requests

All paths start with `url` (it contains the token). Responses are JSON.

| Request | Answer |
|---|---|
| `GET api/hello` | `protocol`, `kind`, `project`, `engine`, `pid`, `services` (names), `topics` (state topics) |
| `GET api/events?topics=a,b` | A stream of state events (Server-Sent Events): `event: <topic>` and `data: <JSON>` lines, then a blank line |
| `GET`/`POST <service>/...` | A feature added by the engine, such as `penpot/` in the editor |

The topic `stats` sends the performance numbers about four times a second: frame times, and when present `game` (tick, simulation time), `session` (players, round trip, traffic), `render` (draw calls, GPU time, memory) and `audio` (voices).
Requests are handled on the engine's main thread between frames, so a service changes engine state safely.

### Security

The server listens on `127.0.0.1` only, and the token in every path comes from the info file, which only programs on this computer can read. A request with a browser `Origin` header is refused unless it comes from the server itself or the service allows that origin (the Penpot service allows Penpot), so a web page cannot call it.

### Protocol version

`protocol` is the version of this contract's paths and answers (now 1). A tool states the version it was made for in its manifest; the editor does not open a tool made for another version.

`tools\live_probe.ps1` in the engine is a small client that does all of the above; it is the reference for tools written in other languages.

## Tool manifest

A tool folder has `mealkit-tool.txt` next to the program:

```text
# MealKit tool manifest
@format tool 1
name Audio
exe mealkit-audio.exe
version 0.1.0
protocol 1
opens .table .wav
```

| Key | Meaning |
|---|---|
| `name` | Name in the Tools menu (required) |
| `exe` | The program, relative to the manifest folder or absolute (required) |
| `version` | The tool's version, shown in the menu |
| `protocol` | The live connection version the tool was made for (required) |
| `opens` | File extensions the tool edits (for "open with" in a later asset browser) |

The editor looks in folders given with `--tool-path`, then `%LOCALAPPDATA%\MealKit\tools\`, then `toolPath` lines of its settings file, and starts a tool as `"<exe>" --project "<project folder>"` with the manifest folder as the working folder.

## Runtime parts

A tool can have a part that runs inside the game (the audio tool's mixer, [MealKit Audio](https://github.com/MealKit-Engine/MealKit-Audio)). That part does not include engine headers, and the engine takes it like any external library: a fixed version in `third_party/<lib>/` with its license, inside the release exe budget ({engine}`docs/CODING_MODEL.md` "외부 라이브러리 두기"). `tools\check_libs.ps1` checks that it uses no engine header or macro. While both change, the engine builds the part from a local checkout (`-DMEALKIT_MKAUDIO_DIR` for the audio runtime).
