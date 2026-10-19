# Multiplayer and determinism

MealKit multiplayer is **deterministic input lockstep**. Peers send only their inputs (8 bytes per player per tick), every PC runs the same simulation, and state hashes detect desyncs.
The host is both a player and the relay. There is no dedicated server.

## Playing together

Started without options, the example opens its title screen. From the main menu you can play solo, host a room, join a room (rooms on the same network are listed by themselves, or type an address), or play with Steam friends when the build has the Steamworks SDK.
In the lobby every player picks a body, marks themself ready and can chat; the host starts when everyone is ready. A match counts down, runs for two minutes and shows the results; then the host takes everyone back to the lobby for the next match.

The same rooms can be opened from the command line, which skips the menus:

```bat
sandbox.exe                          :: title screen and menus
sandbox.exe --host                   :: host a room (UDP 27015) and wait in the lobby
sandbox.exe --join 192.168.0.10      :: join
sandbox.exe --steam                  :: create a Steam friends lobby (needs the Steamworks SDK)
sandbox.exe --scene my.scene         :: play another scene
sandbox.exe --system-info            :: print CPU and GPU features (exit code 2 below the minimum spec)
sandbox.exe --help                   :: all options
```

- Every player must use **the same executable, the same scene and the same model files**. Otherwise the connection is refused (this protects determinism).
- To connect from another PC over UDP, allow `sandbox.exe` in the host's firewall, and set up port forwarding across the internet. With Steam neither is needed.
- To test with several windows on one PC, use `--host --local` so the firewall prompt does not appear. Rooms hosted with `--local` are announced on 127.0.0.1 only, so other windows on the same PC still list them.
- To try a match as it feels over the internet without a second PC, add `--net-lag 120 --net-jitter 30 --net-loss 2` to each window (added round trip time, extra random delay, dropped packets).
- Rooms announce themselves on the local network every second while they wait in the lobby (UDP port 27199). The join screen lists rooms of the same game; a room with a different version or different game data is grayed out.

Game controls in the example: `WASD` or a gamepad's left stick move, `Space` jump, left click push, right drag or right stick camera, wheel zoom, `F8` debug shockwave, `Enter` chat, `Esc` or `Start` pause menu, `V` vsync, `F12` screenshot. The bindings are in `assets/input.bindings` (see {doc}`input`).

## Screen flow

The screens from the title to the results are game code, so each game changes them freely: the example keeps them in `source/app/Flow.cpp` and one `.ui` file per screen (`title`, `menu`, `join`, `lobby`, `loading`, `pause`, `results`, `message`).
Opening and closing rooms is engine work, and the game only calls `ctx.match` (`mealkit/game/MatchService.h`):

| Call | When |
|---|---|
| `playOffline()`, `host()`, `hostOnline()`, `join(address)` | From the menu. Each goes to the lobby; `join` also takes the address of a room from `rooms()` (fill the list while the join screen is open with `setBrowsing(true)`) |
| `start()` | Host, in the lobby |
| `returnToLobby()` | Host, after the results. Every player goes back to the lobby; one session hosts any number of matches |
| `leave()` | Anywhere: closes the session and goes back to the menu |
| `phase()`, `error()` | Which screen to show: menu, connecting, lobby, match or ended (with the reason) |

In the lobby, `ctx.session` has the players (`lobbyMembers()`: name, ready, host, the loadout they picked), `setLocalName`, `setLocalReady` and the chat (`sendChat`, `chatLog`). Chat lines go through the host, so everyone sees them in the same order; they are not part of the match and are not recorded.
When the match must end is decided by the simulation (the example's `MatchPhase`: countdown, playing, finished), so every peer shows the results on the same tick.
The engine calls `GameInstance::start` one frame after the session starts the match (so the loading screen is drawn) and `GameInstance::stop` when the match is over.
A game that draws these screens returns `true` from `GameInstance::menus()`; the engine then leaves `Esc` and `Enter` to the game.

## Commands

Inputs are only 8 bytes per player per tick. Things that happen now and then and change the simulation, such as debug cheats, votes or changing a setting during a match, are sent as **commands**.
Never change the simulation state directly from the view side: the other peers and the shadow simulation would not see the change, and the game would desync.

```cpp
// sim/Commands.h: a command type (no strings or containers, it is copied as bytes)
MEALKIT_STRUCT(DebugShockwave) { MEALKIT_FIELD(u32, pushes, 1, "Pushes"); };

// view side: send it
mealkit::sim::sendCommand(ctx.session, DebugShockwave{});

// World::step(), first thing: handle the commands of this tick
mealkit::sim::forEachCommand(tickInputs, [&](const mealkit::sim::Command& c) {
    if (DebugShockwave d; c.read(d)) shockwave(world, c.player, d);
});
```

The host puts each command on the next tick it confirms and sends it to every peer together with that tick's inputs, so every peer handles it on the same tick, in the order player number, then send order. A tick carries up to 256 bytes of commands; the rest moves to the next tick.
Commands are part of the tick inputs, so input recordings, rewind and the shadow simulation include them.

## Match start data

Values each player brings into the match, such as a chosen character or equipment, are a **loadout**: a `MEALKIT_STRUCT` of up to 128 bytes without strings.
Before the match, `GameInstance::lobby` sends it with `mealkit::game::setLoadout(session, loadout)`. The host collects every player's loadout from the lobby and sends them all when it starts the match.
The match start (`startWorld`) reads them with `mealkit::game::readLoadout(match, player, loadout)` and copies them into the players' state, which is hashed like any other state. Input recordings keep the loadouts, so replays rebuild the same match.

## Determinism rules

Lockstep works only if every PC computes bit-for-bit the same result. The game's simulation code lives in `sim/`, and `World::step()` calls the system functions in a fixed order.
Before every build, **SimCheck** checks the `sim/` files. When a rule is broken, it prints `file(line,col): error SIMnnn` with what to use instead, and stops the build.

The rules themselves (math functions, floating-point options, random numbers, iteration order, state declarations) change together with engine code, so their canonical text is in the engine's {engine}`coding model <docs/CODING_MODEL.md>` ("Determinism rules"). In short:

- Use only arithmetic and `sqrt`. For angles, use `detSin`, `detCos` and `detAtan2` from `mealkit/core/DetMath.h`.
- Use only `Pcg32` for random numbers.
- Keep iteration and creation order fixed. Do not iterate hash maps or depend on pointer addresses.
- The simulation never reads real time, the camera, the frame rate or rendering LOD.
- State that lives across ticks is declared with `MEALKIT_FIELD` inside `WorldState`.

## Running without a window (headless)

```bat
sandbox_headless.exe --seed 7 --exit-tick 900 --hash-log a.txt --record-inputs match.rec
sandbox.exe --headless --replay-inputs match.rec --hash-log b.txt   :: rerun the same inputs and compare the recorded hash every tick
sandbox_headless.exe --host --local --players 2 --exit-tick 900      :: networking works as usual (windowed peers can connect too)
sandbox_headless.exe --help
```

- No window, renderer or audio is created. Only `World` runs. Input is always bot input, and alone it runs as fast as it can (900 ticks in about 1–2 seconds).
- `sandbox_headless.exe` links only `sim/` + `app/Headless.cpp` with the engine core (`mealkit_core`, no renderer or window). On Linux (x64) and macOS (ARM64) with Clang, only this is built. The shipped exe's `--headless` runs the same code.
- `--hash-log`: one `<tick> <hash>` line per tick. The windowed game (`sandbox.exe --bot --hash-log`) writes the same file.
- `--record-inputs` (also in the windowed game) saves the confirmed inputs and the hash of every tick. `--replay-inputs` reruns them without a network and prints `REPLAY ok` or the first tick that differs.
  To compare builds, compilers or operating systems, do not run bots separately: replay **the same recording** in each build (for example `build\ClangCL\bin\sandbox_headless.exe --replay-inputs match.rec`).
- A game project gets `<name>_headless` by putting `MEALKIT_HEADLESS_GAME(class)` in `source/app/Headless.cpp` (`mealkit/game/Headless.h`, coding model "Headless entry point").

(steamworks)=
## Steamworks

Valve's terms do not allow the Steamworks SDK in the repository. Download it yourself and CMake detects it.

1. Sign in to https://partner.steamgames.com/ with a Steam account → **download the SDK** (`steamworks_sdk_xxx.zip`).
2. Unzip it and put the whole `sdk` folder at `third_party/steamworks/sdk`. These two files must exist:
   - `third_party/steamworks/sdk/public/steam/steam_api.h`
   - `third_party/steamworks/sdk/redistributable_bin/win64/steam_api64.lib`
3. Run `build.bat` again. If the build log shows `Steamworks SDK found`, it is on. `steam_api64.dll` and `steam_appid.txt` are placed next to the executable automatically. The app ID is `mealkit_add_game(... STEAM_APP_ID <id>)` (default 480).
4. With the Steam client running, `sandbox.exe --steam` creates a lobby and opens the friend invite window (`I` opens it again). When a friend accepts, the game starts with `+connect_lobby` and joins automatically.

- During development, use Valve's test app ID **480 (Spacewar)**. For release, change `STEAM_APP_ID` in the project's `CMakeLists.txt` to your own app ID from Steam. If it is not 480, `steam_appid.txt` is not put in the release folder (Steam launches the game).
- The Steam backend (`engine/src/mealkit/online/OnlineSteam.cpp`; games use only `online::Service`) **has been compiled and linked** against SDK v1.65. Connecting through real Steam lobbies and relays has not been verified yet.
- `third_party/steamworks/` is in `.gitignore`.
- Online features (accounts, lobbies, invites, relay) go only through `online::Service`. Game code never calls a platform SDK directly. The Editor build always uses the "none" backend.
