# Debug

This page explains how Dear ImGui is connected to the engine's window and renderer, and how the F1 overlay of development builds works.
How to write debug windows for a game is in {doc}`../../manual/debug_ui`. The code is in {engine}`engine/src/mealkit/debug`.

`debug` comes after `online` and before `input` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존"). It uses `platform` (the window) and `render` (the device and the command list).
Debug UI is only for development tools; game UI is a different system (see {doc}`ui`). Why the two are separate is in {engine}`docs/CODING_MODEL.md` ("코드로 짜는 UI").

## When it is built

The folder and Dear ImGui are compiled only when `MEALKIT_DEBUG_UI` is on ({engine}`cmake/MealKit.cmake`, {engine}`engine/CMakeLists.txt`):

| Build | Debug UI |
|---|---|
| Editor | Always on. ImGui is inside `mealkit.dll`, so the editor and the game DLL share one ImGui and one context. |
| Development game exe | On by default. ImGui is linked into the static engine library. |
| Release (`build.bat Export`) | Off. The exe contains no ImGui at all. |

ImGui's own sources are compiled as a separate object library with warnings off, then added to the engine target, so the engine's strict warning level does not apply to outside code.
The engine target passes `MEALKIT_DEBUG_UI=1` and the ImGui include path on to the game, which wraps its debug code in `#if MEALKIT_DEBUG_UI`.

## ImGuiLayer

`debug::ImGuiLayer` ({engine}`engine/src/mealkit/debug/ImGuiLayer.h`) connects Dear ImGui to a MealKit `Window` and `Renderer`. The window side (ImGui's Win32 backend) is in the platform layer ({engine}`engine/src/mealkit/platform/ImGuiPlatform.h`), and the drawing side (ImGui's DX12 backend) is in the RHI backend (`rhi::imguiInit`, `imguiRender` in {engine}`engine/src/mealkit/rhi/Rhi.h`), so the layer itself calls no OS or graphics API.

`init` ({engine}`engine/src/mealkit/debug/ImGuiLayer.cpp`):

1. Creates the ImGui context with keyboard navigation and docking. When an ini path is given, window positions are saved there (the editor does this, the game overlay does not).
2. Reads the window's DPI scale and scales the style and the fonts by it. The style is ImGui's dark style with MealKit's own colors and rounding.
3. Loads Segoe UI for Latin text and merges Malgun Gothic for Korean, both at 16 pixels. Malgun Gothic alone would show the backslash as ₩. An icon font is merged on top: Segoe Fluent Icons on Windows 11, Segoe MDL2 Assets on Windows 10 (the same code points), moved down 3 pixels to sit in the middle of a Korean line. ImGui 1.92 builds glyphs when they are first used, so the full Hangul range is not baked in advance.
4. Starts the platform part (`imguiPlatformInit`), which starts the Win32 backend and installs a message hook on the window, so ImGui sees the window messages.
5. Starts the drawing part with the renderer's RHI device (`rhi::imguiInit`). The DX12 backend gets the device, queue, frames in flight, and the overlay render target format (no gamma conversion, the same view the game UI uses).

The DX12 backend needs shader-visible descriptors for its font texture and for user textures. It borrows them from the texture slots of the device's bindless descriptor heap, through allocate and free callbacks that work on the device's list of free slots.

Each frame:

- `newFrame` deletes textures that were released and that the backend has finished with, then starts a new ImGui frame.
- `render(renderer, frameActive)` always calls `ImGui::Render()`, so the ImGui frame is closed even when nothing is drawn (a minimized window). When the renderer's frame is open, it binds the overlay view (`beginOverlay`) and records ImGui's draw data into the renderer's command list (`rhi::imguiRender`).

`createTexture` makes an RGBA texture that `ImGui::Image` can draw; the backend uploads it in the next frame. `releaseTexture` only marks it, and it is deleted a few frames later when the backend reports that the GPU is done with it.

## The F1 overlay

In a development game exe, the engine's main loop ({engine}`engine/src/mealkit/game/GameMain.cpp`) owns one `ImGuiLayer`:

- It is created the first time `F1` is pressed, or at start with `--debug-ui`. Creating it reads fonts, so a session that never opens the overlay does not pay for it.
- `F1` shows and hides it. While it is shown and ImGui wants the keyboard or the mouse (`WantCaptureKeyboard`, `WantCaptureMouse`), the game does not get that input.
- The window "MealKit" sits at the bottom left and sizes itself to its content. It shows the performance lines of `game::FrameStats` (frame time, draw calls, network and sound numbers, one line per item) and the reminder `F1: hide | V: vsync | F12: screenshot`. The text is refreshed once per report period of 0.25 seconds.
- Then the game's own `GameInstance::debugUi(ctx)` runs inside the same ImGui frame.

The overlay is drawn after the 3D scene and after the game UI, so it is always on top.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Immediate mode GUI | Dear ImGui | The debug UI is rebuilt from data every frame, so debug windows need no saved widget state. |
| Compile-time feature switch | `MEALKIT_DEBUG_UI` | Debug UI code is removed from release builds by the preprocessor, which keeps ImGui out of the shipped exe. |
| Backend adapter | `ImGuiPlatform.cpp`, `Dx12ImGui.cpp` | Plugs ImGui's stock Win32 and DX12 backends into the engine's window message hook and the RHI device. |
| Free-list descriptor allocator | `allocSrv` / `freeSrv` in `Dx12ImGui.cpp` | Texture slots of the bindless heap whose free slots are kept on a stack. |
| Deferred destruction | `releaseTexture`, `newFrame` | A texture is deleted only after the backend says the GPU stopped using it, which avoids freeing memory still in flight. |
| Font merging | `init` | Several fonts form one ImGui font: Latin, Korean and icons, each from the font best suited for it. |
| Lazy start | `GameMain.cpp` | The overlay and its fonts are created on first use. |
| Input capture | `GameMain.cpp` | ImGui's `WantCapture*` flags decide whether the game sees keys and the mouse this frame. |
