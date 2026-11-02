# Your first project

Like Godot, MealKit has **one general-purpose editor** that opens many **game project folders**. See {doc}`../manual/projects` for what a project folder contains.

## Opening the project manager

- Run `editor.bat` in the engine folder (it builds the editor first if needed), or run `build\Editor\bin\MealKitEditor.exe` directly. The project manager opens, similar to Godot's.
- It offers Create, Import, search and the editor language (Korean/English). In the list you can star a project (favorites), click the icon, the name (= the exe name, `tools\rename_project.ps1`) or the folder path (moves the folder) to change it, and double-click to open the project.
- The icon you pick (`icon.png`, project setting `icon`) becomes the game exe icon in release builds. Without one, the MealKit icon is used.
- A project folder's `editor.bat` runs `MealKitEditor.exe --project <that folder>`. The engine repository's reference sample `samples/sandbox` opens with `editor.bat sample [scene]` (open `samples/coop` the same way with `--project`).

## Creating a project from the command line

```powershell
powershell -ExecutionPolicy Bypass -File tools\new_project.ps1 -Name MyGame          # → D:\GameEngine\MealKit\MyGame
powershell -ExecutionPolicy Bypass -File tools\new_project.ps1 -Name MyGame -Path E:\Games
powershell -ExecutionPolicy Bypass -File tools\new_project.ps1 -Name MyGame -Template empty
```

`-Template` picks the starting point (the editor's Create New Project window has the same choice):

- `arena` (default) copies the example game's code and `assets/`: a physics party versus game with AI, boxes, jump pads and cutscenes.
- `empty` starts with one character per player on a floor, plus the title, lobby, pause and results screens. The screen flow code (`source/app/Flow.cpp`) and its screens are the same as the example game's.

Both fill in the files from `templates/project` (`mealkit.project`, `CMakeLists.txt`, `build.bat`, `editor.bat`, `.vscode/`, `README.md`, `CLAUDE.md`), and `mealkit.project` records the template in `templateName`.
The engine location is the `engine` line in the project's `mealkit.project`, and the engine's `tools\build_project.bat` does the actual build.
The project's `CMakeLists.txt` includes `cmake/MealKit.cmake` and creates the game exe, the game DLL and the release target with a single `mealkit_add_game(...)`.

## Upgrading a project

The engine version is in the engine's `VERSION` file. When the project template changes, the version goes up, and the editor suggests upgrading a project when it opens one.
`tools\upgrade_project.ps1 -Project <folder>` replaces only template files you have not changed (tracked by hashes in `.mealkit-template`) and leaves your changed files next to the new version as `.new`.
