# Tools

MealKit is a family: the engine and its general-purpose editor in the middle, and small tools for each role around them, such as an audio tool for sound designers. Each tool is its own program in its own repository (free, MIT). The editor opens them from the **Tools** menu, and they work on the same project folder.
Work that a good free tool already does stays in that tool with an engine plugin: models in Blender ({doc}`blender`), screens in Penpot ({doc}`ui`).

## Opening a tool

**Tools** in the editor's menu bar lists the installed tools. Choosing one starts it with the open project (`<tool> --project "<project folder>"`).
A grayed-out tool cannot be opened; hover over it to see why:

- **Needs tool protocol N**: the tool was made for a different version of the editor connection. Update the tool or the engine.
- **Program not found**: the tool's manifest names a program that is not there.

**Rescan Tools** looks again after installing a tool, and **Open Tools Folder** opens the default install folder.

## Installing a tool

A tool is a folder with a manifest file `mealkit-tool.txt` next to its program. Put the folder in `%LOCALAPPDATA%\MealKit\tools\` (for example `%LOCALAPPDATA%\MealKit\tools\audio\`), then **Tools > Rescan Tools**.

To keep tools somewhere else, add a `toolPath` line to the editor settings file `%LOCALAPPDATA%\MealKit\editor_settings.txt`, one line per folder:

```text
language ko
toolPath D:\MealKitTools
```

A `toolPath` folder can be a tool folder itself or a folder of tool folders. `MealKitEditor.exe --list-tools` prints what the editor finds, and `--tool-path <folder>` adds a folder for one run (useful while building a tool).

## Live connection

While a development build of the game or the editor runs, tools can connect to it to change values and read its state without restarting, like FMOD's Live Update. The editor and every development game window (the game's `build\Release`, `Debug` or `Profile` exe) open a small server on this computer only, and write how to reach it in the project's `build\live\` folder. Release builds made with **Build > Release Build** do not have it.

`tools\live_probe.ps1` in the engine shows what is running for a project:

```bat
powershell -ExecutionPolicy Bypass -File tools\live_probe.ps1 -Project D:\Games\MyGame -Events 2
```

How tools use the connection is in {doc}`../reference/tool_contract`.

## Files tools share

Tools read and write the project's files, so every MealKit text file (tables, tuning, scenes, `.ui` screens, string tables, `mealkit.project`) has a **format line** after its comment header, for example `@format table 1`. Keep that line when you edit a file by hand. When a format changes, the engine and the tools read the older versions and write the new one.
