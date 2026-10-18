# Player settings

Every game gets the same settings without writing them: display, audio, controls, keys and game options. The engine stores them, applies them and opens a standard settings screen; the game only restyles the screen.

## What is in it

| Tab | Settings |
|---|---|
| Display | Window mode (windowed, borderless window, fullscreen), resolution of the window, vertical sync, frame limit, render scale, graphics quality, field of view, brightness |
| Audio | Master, music, effects, interface and voice volume (the audio buses), mute when the window is in the background |
| Controls | Mouse and gamepad sensitivity, invert Y |
| Keys | One row per button action: press it, then press the new key (Esc cancels). A key used by another action is marked. Reset restores the project's keys |
| Game | Language, interface size, subtitles |

Fullscreen is a borderless window the size of the monitor. Render scale, graphics quality and brightness are stored now and used by the graphics features of stage 2.
When the resolution or window mode changes, a box asks to keep it and reverts after 15 seconds without an answer.

The values are saved in the user folder (`%LOCALAPPDATA%\<game>\settings.ini` on Windows), next to the player's key bindings. They are not part of the content hash, and the simulation never reads them: sensitivity and invert are applied to the input actions before the game turns them into its tick input.

## Using it from the game

- Any button in a `.ui` file with `button settings.open` opens the settings screen. In code: `ctx.settings.open()`.
- `ctx.settings.values()` reads the settings on the view side, for example `values().display.fov` for the camera.
- The look of the screen is `assets/ui/settings.ui`. Change it freely, but keep its bindings (`tabs`, `rows` and the row fields) and its `settings.*` actions. The text comes from the string table keys `settings.*`, `action.<id>` and `language.<code>`.

Automated runs (`--exit-tick`) use the default settings and do not save, so the settings on one PC do not change test results. Giving `--size`, `--vsync` or `--fps` makes that run use the command line instead of the display settings. `--settings` starts with the screen open.
