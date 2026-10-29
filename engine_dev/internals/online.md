# Online

This page explains the online service layer: the one interface the game uses for accounts, lobbies and relayed connections, and how the build chooses the Steam or the "none" backend.
How to set up Steam for a project is in {doc}`../../manual/multiplayer`. The code is in {engine}`engine/src/mealkit/online`.

`online` comes after `asset` and before `debug` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"). It uses `net` for the `Transport` and `Address` types, so a relayed connection plugs into the same lockstep session as a direct UDP one.
Why there is one layer instead of calling platform SDKs directly is in {engine}`docs/CODING_MODEL.md` ("Online features").

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
| EOS | {engine}`engine/src/mealkit/online/OnlineEOS.cpp` | A game build where `third_party/eos/sdk` has `Include/eos_sdk.h` and `Lib/EOSSDK-Win64-Shipping.lib`, and `third_party/eos/credentials.txt` exists. CMake defines `MEALKIT_EOS=1`, writes the portal values into `EosCredentials.h` in the build folder, links the SDK and copies `EOSSDK-Win64-Shipping.dll` next to the game exe. |
| None | {engine}`engine/src/mealkit/online/OnlineNone.cpp` | Every other build: no SDK, or the Editor build. |

The CMake option `MEALKIT_ONLINE` picks the backend: `Auto` (default) uses Steam when its SDK is there, otherwise EOS, otherwise none. `Steam` and `EOS` force one and stop the configure step when its files are missing. `build.bat EOS` builds into `build\EOS` with `-DMEALKIT_ONLINE=EOS`.
The SDKs are not in the repository, so a fresh checkout always builds with "none". The Editor build never uses an online backend, because multiplayer play in the editor connects its player windows over local UDP.
Because all files implement the same class, game code is the same for every backend. Console services (stage 5) will be more files of the same kind.

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

## The EOS backend

`OnlineEOS.cpp` wraps the Epic Online Services SDK:

- `init()` calls `EOS_Initialize` and `EOS_Platform_Create` with the values from `credentials.txt`, then logs in with **EOS Connect and a device ID**, so players need no Epic account. The first login on a PC creates the device ID and the EOS user. `init()` waits for the login for up to 15 seconds.
- `net::Address::userId` is a 64-bit hash of the Product User ID string. The backend keeps a table from hash to Product User ID, filled from lobby members and received packets.
- `createLobby` creates a lobby and sets the attribute `MKCODE` to a random six-digit code. `lobbyId()` returns that code, and `joinLobby(code)` searches for the lobby with that attribute and joins it. `inviteFriends()` writes the code to the log, because there is no friend list without Epic accounts.
- `setLobbyOwner` calls `EOS_Lobby_PromoteMember`.
- `createTransport()` returns a transport on EOS P2P (socket `mealkit`, channel 0, unreliable unordered). Every connection request is accepted; the lockstep session checks who may join.
- EOS P2P packets are at most 1170 bytes (`EOS_P2P_MAX_PACKET_SIZE`), so the lockstep packet limit is 1170 bytes for every transport.
- One OS user has one device ID, so two game processes on the same PC log in as the same EOS user. Test with two PCs.
- With the Steamworks SDK also present, CMake defines `MEALKIT_EOS_STEAM=1` and links Steam into the EOS build. `init()` then calls `SteamAPI_Init`, gets a web API ticket for the identity `epiconlineservices` and logs in with `EOS_ECT_STEAM_SESSION_TICKET`. If Steam is not running or the portal has no Steam provider, it logs in with the device ID. `inviteFriends()` opens the Steam invite window with the connect string `+connect_lobby <code>`, and Steam rich presence `connect` lets friends join from their friend list. An accepted invite arrives through `GameRichPresenceJoinRequested_t` (`takeJoinRequest`), or as the `+connect_lobby` launch argument.
