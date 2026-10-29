# Settings

This page explains how player settings work inside: the `settings.ini` file, how each setting reaches the engine, and how the standard settings screen is built from the setting declarations.
How players and games use settings is in {doc}`../../manual/settings`. The code is in {engine}`engine/src/mealkit/settings`.

`settings` is the last folder of the screen side. It comes after `feedback` and before `game` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"), because it applies values to almost everything before it: the window, the renderer, sound, text, UI and input.
The simulation never reads settings. SimCheck blocks `mealkit/settings/` headers in `sim/`, and settings are not part of the content hash.

## The declaration is the schema

The settings are one `MEALKIT_STRUCT` with four sections ({engine}`engine/src/mealkit/settings/Settings.h`):

| Section | Fields |
|---|---|
| `display` | window mode, width, height, vsync, frame limit, render scale, graphics preset, field of view, brightness |
| `audio` | master, music, effects, interface and voice volume, mute in the background |
| `controls` | mouse sensitivity, invert mouse Y, gamepad sensitivity, invert gamepad Y |
| `gameplay` | language, interface scale, subtitles, network status |

There is no separate file schema: the field declarations give the names, types and defaults. `settings.ini` is written and read with the reflection text functions (`reflect::saveTextFile`, `loadTextFile`) as `path value` lines, for example `display.vsync true`.
The file is in the user folder (`game::userFolder`), next to the player's key bindings. A field the file does not have keeps its default, so new settings in a game update need no file migration.

## Applying settings

`settings::Service` ({engine}`engine/src/mealkit/settings/Settings.cpp`) is created once by the engine (the release exe, editor play, player windows). `init(targets, file)` reads the file and applies everything.
`Targets` lists where to apply values; a missing target is skipped. In editor play the window is not given, so a setting never changes the editor's own window.

| Setting | Applied to |
|---|---|
| window mode, width, height | `Window::setMode` (only when they changed, or at start) |
| vsync | `Renderer::setVsync` |
| frame limit | `FrameLimiter::setTargetFps` |
| volumes | `audio::Engine::setBusVolume` for the buses `master`, `music`, `sfx`, `ui`, `voice` |
| language | `loc::Strings::load(language, project language)`; empty means the project language |
| interface scale | `ui::System::setScale` |
| sensitivity and invert | `input::Actions::setLookSettings` |

Render scale, graphics preset, field of view, brightness, subtitles and the network status are stored and shown on the settings screen, but the engine does not apply them itself; a game reads them with `ctx.settings.values()`.
Muting in the background is read by the engine loop every frame ({engine}`engine/src/mealkit/game/GameMain.cpp`).

Every change goes through `change()`: it applies the new values and saves the file at once.

### Confirming display changes

A new window mode or resolution can leave the player with a black or unusable screen. So when one of them changes, the service remembers the previous display settings and starts a 15-second countdown.
The screen shows "keep" and "revert" with the seconds left. If the player does not keep the change in time, `update` puts the previous values back, applies and saves them.

## The standard settings screen

The engine opens `assets/ui/settings.ui` when any screen sends the action `settings.open`, or when the game calls `ctx.settings.open()`. It is a normal UI screen (see {doc}`ui`) on layer 100, above game screens.

The screen is bound to an engine view model, `SettingsVm`:

- `tabs`: a list of tabs (`label`, `active`): display, audio, controls, keys, gameplay.
- `rows`: a list of up to 40 rows. Each row has a label, a value text, `on` for toggles, `value01` for sliders (0..1), flags for its kind (`isToggle`, `isSlider`, `isChoice`, `isKey`) and `warning`.
- `confirm` and `confirmText` for the display countdown.

So `settings.ui` contains only one row template per kind, shown or hidden by those flags. The rows are not written in the file; they come from tables in the code that name a setting path and a kind (with minimum, maximum and step for sliders).
Labels come from the string table: `settings.tab.<tab>`, `settings.<path>`, and `settings.<path>.<value>` for enum choices.

Choice rows get their choices from the data:

- resolution: the display sizes the window reports,
- frame limit: none, 30, 60, 120, 144, 240,
- language: every file in `assets/strings`, labelled `language.<code>`,
- enums (window mode, preset): the enum's value names.

`update` runs every frame after the UI update and before the game. It handles the screen's actions: `settings.tab`, `settings.changed` (a toggle or slider wrote into the view model; the value is read back, slider values are mapped to the range and rounded to the step), `settings.prev` and `settings.next` (choices), `settings.reset` (the current tab back to defaults), `settings.keep`, `settings.revert`, `settings.rebind` and `settings.close`.
Then it fills the view model again from the current values.

### Key rows

The keys tab lists every `Button` action whose name does not start with `ui.` (see {doc}`input`). Each row shows the bound keys and mouse buttons.
When another button action uses the same keys, the row is marked with a warning.

After `settings.rebind`, the row waits for the next key press:

- `Escape` cancels. `Escape` and `Enter` themselves cannot be bound, because they operate the menus.
- Any other key with a name becomes the action's only key. The new binding is saved at once to the player's `input.bindings` file, which holds only rows that differ from the project.

Resetting the keys tab puts every action back to the project's bindings and saves the player file (which removes it when nothing differs).

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Schema from field declarations | `MEALKIT_STRUCT(Settings)` | One declaration gives the file format, the defaults and the paths the screen uses. |
| Reflection text serialization | `reflect::saveTextFile` / `loadTextFile` | Writes and reads `path value` lines; missing fields keep their defaults. |
| Apply on change | `Impl::change`, `apply` | Each change is applied and saved at once, so there is no separate apply button and nothing is lost on a crash. |
| Optional targets | `Service::Targets` | Values are applied only to the systems that exist, so the same service works in the game, editor play and tests. |
| Timed confirm with rollback | `confirming`, `revert` | Risky display changes revert after 15 seconds unless the player keeps them. |
| Rows generated from data | `buildRows`, `fillVm` | Rows come from tables of setting paths and from enum names, display sizes and string files, not from the `.ui` file. |
| View model list binding | `SettingsVm` | One row template per kind in `settings.ui` is repeated for every row through a `MEALKIT_LIST`. |
| Key capture for rebinding | `Service::update` | Waits for the next key press and writes it into the action's binding, with menu keys excluded. |
| Duplicate binding warning | `fillVm` | Marks rows whose keys another button action also uses. |
