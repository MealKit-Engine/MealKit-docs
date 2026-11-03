# Debug UI

Screens for development (performance numbers, cheat buttons, state views) are written in code with [Dear ImGui](https://github.com/ocornut/imgui). They are not game UI: the shipped game does not contain them.

## Where it shows

| Build | How |
|---|---|
| Development game (`build.bat`, `Debug`, `Profile`) | Press `F1` to show or hide the overlay (`--debug-ui` starts with it shown). The engine window "MealKit" shows average and worst frame time, simulation time, draw calls, network and audio numbers (the same numbers as the window title) |
| Editor play mode | Always, as windows over the editor |
| Release build (`build.bat Export`) | Not there: ImGui is not compiled in |

While the mouse or keyboard is over a debug window, the game does not receive it.

## Writing a debug window

The game overrides `GameInstance::debugUi` and wraps the body in `#if MEALKIT_DEBUG_UI`, because release builds have no ImGui:

```cpp
#if MEALKIT_DEBUG_UI
#include <imgui.h>
#endif

void GameSession::debugUi(mealkit::game::GameContext& ctx) {
#if MEALKIT_DEBUG_UI
    if (ImGui::Begin("Sandbox", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::Text("tick %u", sim().world().state.tick);
        if (ImGui::Button("Shockwave")) mealkit::sim::sendCommand(ctx.session, DebugShockwave{});
    }
    ImGui::End();
#endif
}
```

A button that changes the simulation sends a command (see {doc}`multiplayer`), never changes the state directly. Otherwise the other players and the shadow simulation would desync.
In the editor, the game DLL uses the editor's own ImGui inside `mealkit.dll`, so there is nothing to set up.

## Debug drawing

Game code can draw hit areas and paths with `debug::line`, `debug::box` and `debug::text` from `mealkit/debug/DebugDraw.h`. The shapes show while playing in the editor and in development builds of the game (text only while F1 is on). Release builds leave the calls out. You can call them from `sim/` code: they only record what to draw, so they do not affect the simulation.

```cpp
debug::box(center, half, rotation, debug::kRed, 2.0f); // for 2 seconds
debug::line(from, to);                                 // this frame only
```
