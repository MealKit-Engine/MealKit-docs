# Online

This page explains the online service layer: the one interface the game uses for accounts, lobbies and relayed connections, and how the build chooses the Steam or the "none" backend.
How to set up Steam for a project is in {doc}`../../manual/multiplayer`. The code is in {engine}`engine/src/mealkit/online`.

`online` comes after `asset` and before `debug` in the folder order of {engine}`docs/CODING_MODEL.md` ("엔진 폴더 사이 의존"). It uses `net` for the `Transport` and `Address` types, so a relayed connection plugs into the same lockstep session as a direct UDP one.
Why there is one layer instead of calling platform SDKs directly is in {engine}`docs/CODING_MODEL.md` ("온라인 기능").

## The Service interface

`online::Service` ({engine}`engine/src/mealkit/online/Online.h`) is the only way the game and the rest of the engine talk to an online platform:

| Group | Functions |
|---|---|
| Backend | `backend()`, `backendName()`: which backend this build has |
| Life | `init()` (log in), `shutdown()`, `update()` (once per frame), `available()` |
| Account | `localUserId()`, `displayName()` |
| Lobby | `createLobby(maxMembers)`, `joinLobby(id)`, `leaveLobby()`, `inviteFriends()`, `lobbyState()`, `isLobbyOwner()`, `lobbyId()`, `lobbyMemberCount()`, `lobbyOwnerAddress()` |
| Invites | `takeJoinRequest()`: a lobby the player accepted an invite to, or 0 |
| Connection | `createTransport()`: a `net::Transport` that sends through the platform's relay, or `nullptr` |

A lobby moves through `LobbyState`: `None` → `Creating` or `Joining` → `InLobby`, or `Failed`.

Platform SDKs keep global state for the whole process, so there is only one `Service` per process. The program's main creates it and passes it to whoever needs it, instead of making it a global.

## Choosing the backend at build time

There is no backend switch at run time. {engine}`engine/CMakeLists.txt` compiles exactly one implementation file for the same header:

| Backend | File | When |
|---|---|---|
| Steam | {engine}`engine/src/mealkit/online/OnlineSteam.cpp` | A game build (not the Editor build) where `third_party/steamworks/sdk` has `public/steam/steam_api.h` and `redistributable_bin/win64/steam_api64.lib`. CMake defines `MEALKIT_STEAM=1`, links `steam_api64.lib` and copies `steam_api64.dll` next to the game exe. |
| None | {engine}`engine/src/mealkit/online/OnlineNone.cpp` | Every other build: no SDK, or the Editor build. |

The Steamworks SDK is not in the repository, so a fresh checkout always builds with "none". The Editor build never uses Steam, because multiplayer play in the editor connects its player windows over local UDP.
Because both files implement the same class, game code is the same for both backends. EOS (stage 3) and console services (stage 5) will be more files of the same kind.

## The "none" backend

`OnlineNone.cpp` makes every call do nothing:

- `init()` writes a warning that points to the Steamworks section of the manual and returns `false`.
- `createLobby` and `joinLobby` set the state to `Failed`. `createTransport` returns `nullptr`.

Players then connect by IP address with `net::UdpTransport`, as the command line options `--host` and `--join` do.

## The Steam backend

`OnlineSteam.cpp` wraps the Steamworks API:

- `init()` calls `SteamAPI_Init`. It fails when the Steam client is not running or `steam_appid.txt` is missing next to the exe (during development the app id is 480, Valve's test app). It then calls `InitRelayNetworkAccess`, so the relay route is ready before the first connection.
- `update()` calls `SteamAPI_RunCallbacks`. Steam reports results through callbacks, and they run only here, on the main thread.
- `createLobby` asks for a **friends-only** lobby with `CreateLobby`. The result arrives through a `CCallResult`; the lobby then gets the data `engine = mealkit`.
- `joinLobby` works the same way with `JoinLobby`. A `GameLobbyJoinRequested_t` callback stores the lobby of an accepted invite, which `takeJoinRequest` returns once.
- `lobbyOwnerAddress()` is a `net::Address` that carries the owner's Steam ID instead of an IP address.

`createTransport()` returns a `SteamTransport` built on `ISteamNetworkingMessages`:

- `send` calls `SendMessageToUser` with the flags unreliable, no Nagle delay and restart of broken sessions. Lockstep handles lost packets itself by sending unconfirmed inputs again in every packet ({engine}`engine/src/mealkit/net/Lockstep.h`), so unreliable messages are enough.
- `receive` takes up to 64 messages from channel 0 at once into a queue and hands them out one by one.
- Every session request is accepted. The real check happens in the lockstep session, which compares the build and content hashes and refuses a peer that differs.

## How the game uses it

The engine's main loop ({engine}`engine/src/mealkit/game/GameMain.cpp`) with Steam:

1. Calls `online.update()` every frame. A failed lobby stops the program with an error.
2. When the lobby is ready and the network session is still idle, the lobby owner becomes the lockstep host with `session.hostWith(online.createTransport(), ...)` and opens the invite dialog. Everyone else joins with `session.joinWith(online.createTransport(), online.lobbyOwnerAddress())`.
3. The `I` key opens the invite dialog again.

From there on, the lockstep session does not know whether it runs over Steam or UDP.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Interface with link-time implementation | `Online.h`, one of `OnlineSteam.cpp` / `OnlineNone.cpp` | One header, and CMake compiles one implementation. There are no virtual calls and no SDK headers outside the backend file. |
| Pimpl | `Service::Impl` | Keeps backend state (Steam IDs, call results) out of the header, so including `Online.h` never pulls in an SDK. |
| Null object | `OnlineNone.cpp` | A backend whose calls safely do nothing, so callers need no `#if` around online code. |
| Optional SDK detection | `engine/CMakeLists.txt` | The backend is turned on by the presence of SDK files, so a checkout without the SDK still builds. |
| Callback pumping on the main thread | `Service::update` | Steam callbacks run only inside `SteamAPI_RunCallbacks`, so online state changes only on the main thread. |
| Adapter to the transport interface | `SteamTransport` | Wraps Steam networking messages as a `net::Transport`, so lockstep runs over the relay without changes. |
| Batched receive | `SteamTransport::receive` | Fetches up to 64 messages per call into a queue, fewer SDK calls per frame. |
| Admission by hash, not by transport | `onSessionRequest` | The relay accepts everyone; the lockstep session's build and content hash check decides who may play. |
