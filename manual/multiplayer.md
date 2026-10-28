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

- Every player must run **the same game version** (the same simulation code, built for the same kind of platform) **with the same data** (scene, models, tuning, project settings, tables). Otherwise joining is refused and the player is told why: for example "Your game version differs from the host (yours 1.2 / host 1.3)" or "Your game data differs from the host: tuning". The version is shown on the title screen and in the lobby, and rooms of another version are marked in the join list.
- To connect from another PC over UDP, allow `sandbox.exe` in the host's firewall, and set up port forwarding across the internet. With Steam neither is needed.
- To test with several windows on one PC, use `--host --local` so the firewall prompt does not appear. Rooms hosted with `--local` are announced on 127.0.0.1 only, so other windows on the same PC still list them.
- To make the input delay less noticeable, the example draws your own character ahead by the inputs it has sent but not yet run (only on your screen; the simulation is unchanged). Set `prediction.enabled` in `assets/view.tuning` to compare.
- The **input delay** (time between pressing a key and the character moving, which hides the network round trip) is chosen by the host from the players' ping, between `inputDelayMinMs` (60) and `inputDelayMaxMs` (270) in `mealkit.project`, and follows the connection during the match. The lobby warns about players whose ping is above the maximum. `--delay <ticks>` fixes it.
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

During a match the example shows each player's ping next to their name and, when the match waits for someone's inputs for more than 0.15 seconds, "Waiting for P3..." at the top. `ctx.session.pingMs(player)` is the round trip time the host measured to each player (the lobby list has it too, `LobbyMember::pingMs`), and `ctx.session.waitingFor()` is the set of players the match waits for. Players can turn the display off in the settings (Game, network status).

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

## Replays

Because the match is deterministic, the match start values and every tick's inputs are enough to play it again. The game and editor play (alone) record every match to the user folder's `replays/current.rec` and keep it as `replays/<date>_<time>.rec` when the match ends (back to the lobby, leaving, or closing the window). A recording left by a crash is kept the next time the game starts.
Project Settings `keepReplays` sets how many are kept (default 20, oldest are deleted, 0 turns recording off). Automated runs and `--record-inputs` do not keep replays.

- Game: `sandbox.exe --replay <file>` plays it in the window. Your own input is ignored.
- Editor: **File > Open Replay...** (or `--replay <file>`) plays it as solo play, so pause, step one tick, rewind and the State panel work as usual.
- A replay recorded with different game data (scene, models, tuning, project settings) or another build shows a warning and plays anyway. When a tick's state hash differs from the recording, it pauses at that tick.

### Bug reports

Press **F9** in the game to save the current match for a developer: the user folder's `bugreports/<date>_<time>.zip` holds the input recording so far (`replay.rec`), the build and data versions (`info.txt`), the recent log, a screenshot and one line the player writes (development builds ask for it; shipped builds save without a note).
Open the zip with **File > Open Replay...** in the editor (or `--replay <file.zip>`): it replays to the tick where F9 was pressed and pauses there. Project Settings `bugReports` turns the key off.

## When the host leaves

The match also goes on when the host leaves. The host sends everyone a succession list every second, and the first connected player on it takes over: immediately when the host quits, or after 3 seconds of silence during a match when the host crashes (10 seconds in the lobby and while the match loads).
The new host first collects any confirmed ticks other players received and it did not, then continues; the old host's slot gets empty input like any dropped player, and they get it back if they rejoin. On Steam the lobby ownership follows the new host.
With direct IP connections (`--host`/`--join`) this works on a LAN; over the internet the players may not reach each other, and the match ends as before. Check it with `tools\mp_test.ps1 -Headless -Clients 3 -Ticks 3000 -HostLeave`.

## Joining a running match

A match does not end when a client drops. The host stops waiting for that player, their slot gets empty input, and the game is told on the same tick on every peer (the sample removes their character). The match only ends if the host leaves.

- **Coming back**: joining the same host again gives the player their old slot. The host matches them by the session's token (same running game) or by the same lobby name.
- **Joining late**: a new player can join a running match while there is a free slot (up to the room's maximum players).

The joining player stays on the connecting screen while the host sends a snapshot of the world at the current tick (compressed, about 0.5 MB in the sample). Then they fast-forward through the ticks played since, and then play normally. Nobody else waits.

In game code, joins and leaves arrive as an engine command in `World::step` (`sim::readPresence`). A new slot also carries that player's match start data (`p.readLoadout`). See `applyCommands` and `setPresence` in the sample. Try it with `tools\mp_test.ps1 -Headless -Clients 2 -Ticks 3000 -LateJoin`.

## Finding a desync

When peers compute different results, the host sees a different tick hash and everyone shows "Desync!" (the match keeps running). In a multiplayer match every peer keeps a few snapshots, so it can replay to **the tick where the hashes first differed** and write that state to a text dump: the project's `build/desync/` while developing, or the user folder's `desync/` in a shipped game.
Each dump holds the tick hashes, every declared state field and every physics body (position, rotation, velocity). Compare two peers' dumps:

```bat
powershell -File tools\desync_diff.ps1 -A build\desync\desync_..._p1.txt -B build\desync\desync_..._p2.txt
powershell -File tools\desync_diff.ps1 -Folder build\desync   :: every peer of the same match against the first
```

It prints the first diverging tick, the state fields that differ and the bodies that differ, which usually points at the system that broke a determinism rule. `--desync-test <tick>` deliberately nudges one body on that peer to try this out (`tools\mp_test.ps1 -Headless -Clients 1 -DesyncTest 200`).

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

(eos)=
## Epic Online Services (cross-play)

Epic's terms do not allow the EOS SDK in the repository either. EOS lobbies and P2P work on every platform, so cross-play matches use EOS.

1. Download the EOS SDK from https://dev.epicgames.com/portal and put the contents of its `SDK` folder at `third_party/eos/sdk` (`Include`, `Lib`, `Bin`).
2. In the developer portal, create a product and a client (Peer2Peer policy). Write its five values into `third_party/eos/credentials.txt`, one per line:
   ```
   ProductId: ...
   SandboxId: ...
   DeploymentId: ...
   ClientId: ...
   ClientSecret: ...
   ```
3. Run `build.bat EOS`. The build log shows `online backend EOS`, and `EOSSDK-Win64-Shipping.dll` is placed next to the executable.
4. `build\EOS\bin\sandbox.exe --steam` logs in (no Epic account, a device ID) and creates a lobby. The log shows a six-digit **lobby code**. On another PC, `sandbox.exe --steam-join <code>` joins it.

- `third_party/eos/` is in `.gitignore`, so the client secret never goes into the repository. It is built into the game exe, as EOS expects for game clients.
- Two game processes on one PC are the same EOS user. Test joining with two PCs.
- When the Steamworks SDK is also in `third_party/steamworks/sdk`, the EOS build logs in with the **Steam account** (a Steam web API ticket) and `I` opens the Steam invite window. A friend who accepts joins the EOS lobby by its code. The match itself always goes over EOS. This needs Steam under **Identity Providers** in the Epic developer portal (your Steam app ID and its publisher Web API key, so your own Steam app, not 480). Without it the log says `Steam login failed` and the game logs in with the device ID instead.
- Login and lobby creation have been verified with SDK 1.19.2. Joining from a second PC has not been verified yet.
