# Platform

This page explains how the platform folder works inside: the window and input, files and folders, processes, dynamic libraries, dialogs, images, gamepads and sockets, and how the code for each operating system is kept apart.
Platform is the engine's only door to the operating system. Together with `core` it is the first group in the folder order, and the two may include each other; every other folder comes after them (see "엔진 폴더 사이 의존" in {engine}`docs/CODING_MODEL.md`).
The code is in {engine}`engine/src/mealkit/platform`.

## How win32/ and posix/ split

Headers sit where the feature belongs and contain no operating system types: `platform/Window.h`, `platform/Paths.h`, `core/Clock.h`, `net/Socket.h`.
Each operating system gets its own `.cpp` files in `platform/win32/` or `platform/posix/`, and CMake picks one set when it configures the build ({engine}`engine/CMakeLists.txt`). There are no `#ifdef` branches spread through the engine and no virtual interface; one build has exactly one implementation ("그래픽 API와 OS 기능" in {engine}`docs/CODING_MODEL.md`).

Handles such as `HWND` or `HANDLE` are stored as `void*` or `u64` in the headers, so `<windows.h>` never reaches other engine code or game code.
Code that works on every system with the standard library alone stays outside the system folders: `platform/Paths.cpp` (`std::filesystem`) and `platform/System.cpp` (`cpuName` with the CPUID instruction).

| Feature | Header | `win32/` | `posix/` |
|---|---|---|---|
| Time | `core/Clock.h` | `Clock.cpp` | `Clock.cpp` |
| Files and folders | `platform/Paths.h` | `Paths.cpp` | `Paths.cpp` |
| Debugger, dialogs, process id | `platform/System.h` | `System.cpp` | `System.cpp` |
| UDP sockets | `net/Socket.h` | `Socket.cpp` | `Socket.cpp` |
| Window and input | `platform/Window.h`, `Input.h` | `Window.cpp` | - |
| Child processes | `platform/Process.h` | `Process.cpp` | - |
| Dynamic libraries | `platform/DynamicLibrary.h` | `DynamicLibrary.cpp` | - |
| File dialogs | `platform/FileDialog.h` | `FileDialog.cpp` | - |
| Images | `platform/Image.h` | `Image.cpp` | - |
| Gamepads | `platform/Gamepad.h` | `Gamepad.cpp` | - |
| Debug UI window side (Dear ImGui) | `platform/ImGuiPlatform.h` | `ImGuiPlatform.cpp` | - |

`posix/` has only what the headless build needs on Linux and macOS: time, files, sockets and logging. CI builds it to compare tick hashes across platforms. The window, input, dialogs, images and DLL loading come with the editor port in stage 5.

The first four rows are in `MEALKIT_CORE_SOURCES`, which the headless executable links as `mealkit_core`. The rest are in `MEALKIT_FRONT_SOURCES`, linked only by programs with a screen. `Input.h` and `Gamepad.h` are the exception: their types are read by the input actions in the core, so the headers are in the core list while `Window.cpp` and `Gamepad.cpp` stay on the screen side.
The `platform/<os>/` files implement headers from several folders (`net/Socket.h` is one), so the folder order check ({engine}`tools/check_layers.ps1`) skips them and the platform check below looks at them instead. The same script also fails when a core file includes an engine header that is not in `MEALKIT_CORE_SOURCES`. The folder order cannot catch this inside one folder, such as a core file in `game/` including `game/Frontend.h`.

### The check_platform rule

{engine}`tools/check_platform.ps1` (run by `check.ps1`) reads every `.cpp` and `.h` in `engine/src/mealkit` outside `platform/win32/` and `platform/posix/`, and every file in `samples/`. It fails when a line (comments removed) has:

- an operating system or graphics header, such as `<windows.h>`, `<winsock2.h>`, `<dwmapi.h>`, `<xinput.h>`, `<d3d12.h>`, `<unistd.h>`, `<dlfcn.h>` or `<sys/...>`;
- a typical system call, such as `MultiByteToWideChar`, `LoadLibrary`, `CreateProcess`, `QueryPerformanceCounter`, `WSAStartup`, `getenv` or `dlopen`.

Graphics API headers (`<d3d12.h>`, `<dxgi*.h>`, `<vulkan/...>` and the like) are allowed only in the RHI backend folders `rhi/<api>/`. A backend handles window handles and events, so it may also include operating system headers, but the system calls above still go through the platform layer.
When a port to another system starts, only `platform/<os>/` and the RHI backend need new code.

## Window and input

`Window` ({engine}`engine/src/mealkit/platform/win32/Window.cpp`) is one Win32 window.

- **Creating**: the process becomes per-monitor DPI aware (version 2), so sizes are physical pixels and the window follows DPI changes (`WM_DPICHANGED`). The icon is resource 1 of the exe when there is one.
  A caption color in `WindowDesc` turns on the dark title bar and, on Windows 11, paints it with that color through DWM.
- **Modes**: windowed mode centers the window in the monitor's work area. Borderless and fullscreen are both a popup window the size of the monitor; there is no exclusive fullscreen, because a flip model swap chain has the same latency without it. `displaySizes()` lists the monitor's resolutions of at least 800×600, largest first, without duplicates.
- **Messages**: `pumpMessages()` runs once a frame. It starts a new input frame, then handles every waiting message with `PeekMessageW`, so it never blocks. It returns `false` after the window is closed.
- **Hook**: `setMessageHook` lets another module see each message first. The editor and the debug overlay use it to feed Dear ImGui; a non-zero return means the message is handled.

`Input` ({engine}`engine/src/mealkit/platform/Input.h`) is the raw state of keys and the mouse:

- Keys are Win32 virtual key codes. Letter keys use the capital letter (`'W'`), and `key::` has names for the others.
- `keyPressed` compares this frame with the previous one, which `beginFrame()` copies before new messages arrive.
- Mouse movement for camera control comes from **Raw Input** (`WM_INPUT`), so it has no pointer acceleration and does not stop at the screen edge. The cursor position comes from `WM_MOUSEMOVE`.
- Pressing a mouse button captures the mouse to the window until all buttons are up, so a drag that leaves the window still ends.
- When the window loses focus, all keys and buttons are cleared and the cursor is released, so no key stays stuck down.
- Typed text comes from `WM_CHAR`: UTF-16 units (joined when a character takes two) become UTF-8 in `text()`, after the input method has composed them, so Korean works. Backspaces are counted separately (`backspaces()`, key repeat included). Text input widgets use these.
- `close()` makes the next `pumpMessages()` return `false` (a game's Quit button).

Game code does not read `Input` directly. It reads named actions from `input::Actions`, which the engine fills from `Input` and the gamepad (see {doc}`../../manual/input`). `window.input()` is for engine and debug keys.

## Gamepads

`Gamepads` ({engine}`engine/src/mealkit/platform/win32/Gamepad.cpp`) reads four XInput slots (Xbox and XInput-compatible pads). The engine updates it once a frame and passes `first()`, the first connected pad, to the input actions.

- Sticks become -1 to 1 (negative values divide by 32768, positive ones by 32767, so both ends reach exactly 1), triggers 0 to 1. The dead zone is applied later by the actions.
- Asking XInput about an empty slot is slow (about 14 µs per slot), so an unconnected slot is checked only once a second. A connected slot is read every frame.
- Connecting and disconnecting are written to the log.

XInput was chosen over SDL3 because SDL3's gamepad support alone would take about a third of the 5 MB executable budget (see {engine}`docs/DECISIONS.md`, 2026-10-18).

## Paths

{engine}`engine/src/mealkit/platform/Paths.h` handles files and folders. Every path is UTF-8.

### Finding assets

`findAsset(relative)` returns the full path of an asset file, or an empty string:

1. When a project root is set (`setProjectRoot`), it looks **only** in that folder.
2. Otherwise it looks in the executable's folder and up to five folders above it, then in the current folder.

Step 2 lets a development build in `build\Release\bin` find the repository's `assets` folder without copying it. Step 1 exists for the editor: `MealKitEditor.exe` lives inside the engine repository, so without a root it would find the engine's own `assets` instead of the open project's (see {doc}`editor`).

### Reading and writing

- `readTextFile` reads a whole file in 16 KB blocks.
- `writeTextFile` writes to `<file>.tmp` in the same folder, flushes it, and then replaces the original in one step: `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH` on Windows, `fsync` and `rename` on POSIX. A crash or power cut during the write leaves the old file whole. Tuning and other declared text files, tables, `mealkit.project` and saves go through it.
- `openFile` opens a UTF-8 path with `_wfopen_s` on Windows, because the narrow `fopen` there uses the system code page. POSIX paths are already bytes.
- `fileWriteTime` and `fileCreationTime` return a number for comparing (Windows `FILETIME`, POSIX nanoseconds). Linux `stat` has no creation time, so there it returns the write time.

### The user folder

`userDataDirectory()` is the base folder for per-user data:

| System | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%` |
| Linux | `$XDG_DATA_HOME`, or `~/.local/share` |
| macOS | `~/Library/Application Support` |

If none is known, it returns the executable's folder. A game's user folder is `<base>/<project name>` (`game::userFolder`), where key bindings, `settings.ini` and saves live. The editor uses `<base>/MealKit`.

## System

{engine}`engine/src/mealkit/platform/System.h` has small process-wide functions:

| Function | Windows | POSIX |
|---|---|---|
| `cpuName()` | the CPUID brand string (leaves 0x80000002 to 0x80000004), on x64 | the same on x64; empty on ARM64 for now |
| `debugOutput`, `debuggerAttached`, `debugBreak` | `OutputDebugStringA`, `IsDebuggerPresent`, `__debugbreak` | nothing, `false`, `SIGTRAP` |
| `showErrorDialog` | `MessageBoxA` | nothing (the log already has the message) |
| `exitProcess` | `ExitProcess` | `_Exit` |
| `processId` | `GetCurrentProcessId` | `getpid` |
| `userName` | `GetUserNameW` (UTF-8) | `$USER` |

The game and the headless executable log `cpuName()` at start, so determinism reports from different computers say which CPU ran them. The editor puts `processId()` in the names of hot reload copies.

## Process and ChildProcess

{engine}`engine/src/mealkit/platform/Process.h` starts other programs ({engine}`engine/src/mealkit/platform/win32/Process.cpp`):

- **`ChildProcess`** runs a command line through `cmd.exe /s /c "..."` with no window, and sends its standard output and error into one pipe. `/s` removes only the outer pair of quotes, so a quoted path with spaces reaches the command unchanged.
  `poll()` never blocks: `PeekNamedPipe` says how many bytes are waiting, and only those are read. Output is split into lines; a line that is not valid UTF-8 is treated as the console code page (CP949 on Korean Windows) and converted. When the process ends, the last partial line is flushed and the exit code is kept.
  The editor runs `build.bat Editor`, `build.bat Export`, the upgrade script and the layout check this way.
- **`ProcessGroup`** starts several programs and closes them together. They go into a Windows **job object** with "kill on job close", so they end even if the editor crashes.
  Each process starts suspended and is added to the job before it runs, so programs it starts itself are in the job too. Its output goes to a log file. Multiplayer play in the editor starts its player windows this way.
- `launchDetached` starts a program without waiting (the project manager opening a project in a new editor process), and `openInExplorer` opens a folder.

## DynamicLibrary

{engine}`engine/src/mealkit/platform/DynamicLibrary.h` is three functions: `loadLibrary` (`LoadLibraryW`, with the error code in the message on failure), `findSymbol` (`GetProcAddress`) and `freeLibrary`.
The editor uses them to load the game DLL and to swap it during hot reload. Only Windows has them for now, because the editor is Windows only.

## FileDialog

{engine}`engine/src/mealkit/platform/FileDialog.h` opens the system dialogs for the editor:

- `openFileDialog` and `saveFileDialog` use the common dialogs (`GetOpenFileNameW`, `GetSaveFileNameW`). The filters become the `name\0pattern\0...\0\0` string Windows expects. Saving asks before overwriting and adds the default extension when the name has none.
- `pickFolderDialog` uses the newer `IFileOpenDialog` with `FOS_PICKFOLDERS`, because the common dialogs cannot pick a folder.

They return a UTF-8 path, or an empty string when cancelled.

## Image

{engine}`engine/src/mealkit/platform/Image.h` reads and writes pictures for the editor (project icons) with the Windows Imaging Component (WIC), so the engine needs no image library for this.

- `loadImage` decodes PNG, JPEG, BMP, ICO and other formats WIC knows. An ICO file holds several sizes, and the widest frame is used.
- A picture larger than `maxSize` is scaled down with its aspect ratio kept (high-quality cubic filter).
- Every picture is converted to RGBA8 with straight (not premultiplied) alpha.
- `loadImageResource` reads a picture stored in the executable as an `RCDATA` resource, and `savePng` writes RGBA8 as PNG. When the PNG encoder only accepts BGRA, red and blue are swapped first.

The WIC factory is created once, on first use.

## Socket implementation

The UDP socket is declared in {engine}`engine/src/mealkit/net/Socket.h` and implemented in `platform/win32/Socket.cpp` and `platform/posix/Socket.cpp`. Lockstep and the transport above it are described with the network code.

Both versions behave the same:

- IPv4 only. `resolveAddress` accepts `host`, `host:port` or `1.2.3.4:port` and uses `getaddrinfo`.
- The socket is non-blocking. `receiveFrom` returns -1 when nothing is waiting, so the network session polls it without stopping the frame.
- Send and receive buffers are 1 MB.
- `open(port, loopbackOnly)` binds to all addresses or only to 127.0.0.1. Port 0 picks a free port.
- `openShared(port)` binds with `SO_REUSEADDR` (and `SO_REUSEPORT` where it exists), so several processes receive the same broadcast. `enableBroadcast()` allows sending to 255.255.255.255. LAN room discovery uses both.

Windows needs two extra steps:

- `startup()` and `cleanup()` call `WSAStartup` and `WSACleanup` with a reference count, so several users can open and close the socket library. On POSIX they do nothing.
- On Windows, when a UDP packet reaches a closed port, the next `recvfrom` fails with `WSAECONNRESET`. The socket turns this off with `SIO_UDP_CONNRESET`, so a peer that left does not break receiving from the others.

## Techniques used

The algorithms and patterns behind the parts above, with where to find them in the code.

### Structure

| Technique | Where | What it does |
|---|---|---|
| One implementation per build | {engine}`engine/CMakeLists.txt` | Shared headers, and CMake picks `win32/` or `posix/` source files. No virtual calls and no `#ifdef` in callers. |
| Opaque handles | `Window`, `ChildProcess`, `UdpSocket` | System handles are stored as `void*` or `u64`, so headers never include system headers. |
| Static check of the boundary | `tools/check_platform.ps1` | Regular expressions find system headers and calls outside `platform/<os>/` and graphics API headers outside `rhi/<api>/`. |

### Files

| Technique | Where | What it does |
|---|---|---|
| Atomic replace on write | `writeTextFile` | Writes a temporary file in the same folder and renames it over the original, so a crash never leaves a half-written file. |
| Upward asset search | `findAsset` | Looks in the executable's folder and its parents, so development builds find the repository's assets. A project root replaces the search. |
| UTF-8 everywhere | `Paths.cpp`, `win32/*.cpp` | Paths are UTF-8 in the engine and become UTF-16 only at the Windows call (`MultiByteToWideChar`, `u8string`). |

### Input and timing

| Technique | Where | What it does |
|---|---|---|
| Raw Input for mouse movement | `Window::create`, `WM_INPUT` | Registers the mouse as a raw device and adds relative movement, free of acceleration and screen edges. |
| Edge detection with two frames | `Input::beginFrame`, `keyPressed` | Keeps the previous frame's keys, so "pressed this frame" is `down && !wasDown`. |
| Clear on focus loss | `WM_ACTIVATE` | Drops all key and button state, since key-up messages go to the window that has focus. |
| Backed-off polling of empty slots | `Gamepads::update` | Checks empty gamepad slots once a second because each check is slow. |
| Asymmetric stick scaling | `stick` in `Gamepad.cpp` | Divides negative values by 32768 and positive ones by 32767, so both full deflections map to exactly ±1. |

### Processes

| Technique | Where | What it does |
|---|---|---|
| Non-blocking pipe reading | `ChildProcess::readAvailable` | `PeekNamedPipe` before `ReadFile`, so the editor frame never waits for build output. |
| Line assembly with partial buffer | `ChildProcess::m_partial` | Keeps bytes after the last newline until the rest of the line arrives. |
| Encoding detection by validation | `toUtf8Line` | Tries strict UTF-8 first and falls back to the console code page. |
| Job object with kill on close | `ProcessGroup::launch` | Child processes, and the processes they start, end with the editor even after a crash. Starting suspended closes the gap before the process joins the job. |
| Reference-counted library start-up | `net::startup` | `WSAStartup` once for the first user, `WSACleanup` after the last. |
