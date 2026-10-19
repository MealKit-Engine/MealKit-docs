# Net

This page explains how the network layer works inside: the packet transport, and the lockstep session that sends only player inputs between peers.
`net` is the first folder on the simulation side of the layer order. It includes only `core` and `platform` (see "엔진 폴더 사이 의존" in {engine}`docs/CODING_MODEL.md`).
How to play together and the determinism rules for game code are in {doc}`../../manual/multiplayer`. The code is in {engine}`engine/src/mealkit/net`.

## Sockets and transports

`net::UdpSocket` ({engine}`engine/src/mealkit/net/Socket.h`) is a non-blocking IPv4 UDP socket. Its implementation is per platform: {engine}`engine/src/mealkit/platform/win32/Socket.cpp` and {engine}`engine/src/mealkit/platform/posix/Socket.cpp`.
Both set 1 MB send and receive buffers. With `loopbackOnly` the socket binds to `127.0.0.1` only, so a test on one PC does not open the firewall prompt.
On Windows, a UDP socket normally fails its next receive with `WSAECONNRESET` when the other side's port is closed. The engine turns this off with `SIO_UDP_CONNRESET`.

An `Address` is an IPv4 address and port, or a Steam ID when the Steam transport is used.

The lockstep session never uses a socket directly. It uses `net::Transport` ({engine}`engine/src/mealkit/net/Transport.h`), an interface with two functions, `send` and `receive`:

| Transport | Used for |
|---|---|
| `UdpTransport` | IP and port directly: LAN, development, tests on one PC. `host()` and `join()` make one. |
| `online::Service::createTransport()` | A platform relay such as Steam. `hostWith()` and `joinWith()` take any transport. |

## Lockstep

`net::LockstepSession` ({engine}`engine/src/mealkit/net/Lockstep.cpp`) runs deterministic lockstep. Every peer runs the same simulation, and the network carries only each tick's player inputs.
Bandwidth therefore does not depend on how many objects the game has. The reasons for this model are in {engine}`docs/DECISIONS.md`.

The host is a player and also the relay. There is no dedicated server:

1. Each peer, when it runs tick T, submits its own input for tick T + input delay.
2. Clients send their inputs to the host. When the host has every player's input for a tick, it **finalizes** that tick and sends it to all peers in a bundle.
3. A peer can run only finalized ticks. When an input is late, the simulation waits, and drawing goes on.

A player input is 8 bytes (`kInputBytes`). What the bytes mean is up to the game. A session has at most 8 players (`kMaxPlayers`).

### Input delay

The input delay is the number of ticks between sampling an input and running it. It hides the network round trip: while the input travels, the peer still has finalized ticks to run.
The default is 3 ticks (`--delay`), and `hostWith` clamps it to 1–30. An offline session uses 1.

When a match starts, the first input-delay ticks are already finalized with empty inputs, so tick 0 can run at once.

### Order in one tick

`game::Simulation` ({engine}`engine/src/mealkit/game/Simulation.h`) calls the session in this order for every tick:

1. `canExecute(tick)`: the tick is finalized and the session is running.
2. `inputs(tick)`: the finalized `TickInputs` (all players' inputs and the tick's commands).
3. `World::step(inputs)`, then `World::hash()`.
4. `tickExecuted(tick, hash)`: records the state hash for desync checks.
5. `submitLocalInput(tick + inputDelay, input)`: sends the next input.

On the host, `submitLocalInput` finalizes ticks when it can and sends the bundles right away, so a tick does not wait for the next keep-alive.

### Lost packets

UDP packets can be lost. The session does not resend lost packets. It sends **redundantly** instead:

- A client puts every input the host has not confirmed into every input packet (up to 32 ticks per packet). The host answers with the next tick it needs from that client.
- The host puts every finalized tick a client has not confirmed into every bundle, as many as fit in one packet.

Each side also sends at least every 1/30 second (keep-alive), so a lost packet is replaced by the next one.
A packet is at most 1200 bytes, a size that is not split on internet paths.

Ticks are kept in a ring buffer of 256 slots (`kTickWindow`, about 8.5 seconds at 30 Hz). A tick is accepted only while it is less than 256 ticks ahead of the oldest tick still needed (the next tick to run, and on the host also the oldest tick a client has not received), so a slot is never overwritten while it is still in use.

### Lobby and match start

| State | What happens |
|---|---|
| `Connecting` | The client sends a connect request every 0.25 seconds. |
| `Lobby` | The host sends the player count every 0.5 seconds. The client repeats its connect request every second as a keep-alive, and it carries the player's match start data (loadout). |
| `Running` | `startMatch(seed, matchData)` on the host fixes the player count, numbers the players, and sends a start packet (seed, match data, input delay, every player's loadout) every 0.1 seconds until each client answers with its first input packet. |
| `Ended` | A disconnect, a timeout or a rejection. `endReason()` says which. |

A peer that sends nothing for 10 seconds times out. In the lobby it is removed. During a match, the match ends, because lockstep cannot go on without one player's inputs.
A loadout is at most 128 bytes (`kMaxLoadoutBytes`), so the start packet holds 8 players.

### Who can join

The connect request carries two values, and the host refuses a peer when one differs:

- **Build id**: a hash of the compile date and time. Determinism needs the same machine code, so only the same executable can join. `setAcceptOtherBuilds` turns this off for compiler comparison tests (`mp_test -ClientExe`).
- **Content hash**: set with `setContentHash` before `host` or `join`. `game::contentHash` ({engine}`engine/src/mealkit/game/GameData.cpp`) builds it from the scene, models, tuning, project settings and simulation tables, so peers with different data are refused before the match.

The host also refuses a peer when the session is full or the match has already started.

### Commands

Besides the 8-byte inputs, a peer can send a confirmed command of up to 200 bytes (`submitCommand`), for cheats, input delay changes or votes. The client keeps sending it until the host confirms it.
The host puts waiting commands into the next tick it finalizes, in player order and then in the order they were sent. A tick holds up to 256 bytes of commands, including a 2-byte header per command. What does not fit goes into the next tick.
Commands then travel with that tick's inputs, so every peer runs them on the same tick. The typed layer on top is `sim::sendCommand` (see {doc}`sim`).

### Desync detection

Each client puts the hash of its latest executed tick into every input packet. The host keeps its own hashes for the last 256 ticks and compares them, both when a report arrives and when the host runs that tick itself.
When they differ, the host logs `DESYNC at tick N` and sets a flag in every following bundle, so clients know as well. `desynced()` and `desyncTick()` show it to the game.
Only the host compares hashes, and only the latest hash goes into each packet, so the check is cheap. It tells that the states differ, not which state. Finding which state differs is done inside one process by the shadow simulation (see {doc}`editor`).

### Offline

`startOffline` runs a session with one player and no sockets. It uses the same tick and input path, so playing alone runs the same code as a network match.

### Session stats

`stats()` returns `net::SessionStats`: the round trip time to the host and the bytes sent and received per second. `game::FrameStats` shows them in the overlay.

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Deterministic lockstep | `LockstepSession` | Peers exchange only inputs and run the same simulation, so bandwidth is independent of the object count. |
| Host relay (star topology) | `hostReceive`, `finalize` | Clients talk only to the host. The host decides when a tick is final, so all peers see the same inputs without peer-to-peer agreement. |
| Input delay | `beginRunning`, `submitLocalInput` | Inputs are scheduled a few ticks ahead, which hides the round trip. The first ticks start already finalized with empty inputs. |
| Redundant sending instead of retransmission | `sendInput`, `sendBundle` | Every packet carries everything the other side has not confirmed. There are no timers per packet, and one lost packet costs nothing when the next arrives. |
| Cumulative acknowledgement | `inputNext`, `bundleNext`, `commandNext` | Each side confirms "everything before N", which is one number per stream. |
| Bit mask of arrived inputs | `Slot::mask` | One bit per player. A tick is complete when the mask equals all players. |
| Ring buffer of ticks | `slots[tick % kTickWindow]` | Fixed memory for 256 ticks. Each slot stores its tick number, so an old slot is never taken for a new tick. |
| Build and content fingerprints | `buildId`, `setContentHash` | FNV-1a hashes refuse peers with a different executable or different game data before a match. |
| State hash comparison | `tickExecuted`, `flagDesync` | The host compares its own state hash of a tick with the hash a client reports for the same tick. |
| Round trip time with smoothing | `Packet::Bundle` handling | The host echoes the client's send time. The client keeps an exponential moving average (90% old, 10% new sample). |
| Bounds-checked packet reading | `Reader`, `Writer` | Reads past the end set a failure flag and return zeros, so a short or broken packet is dropped instead of reading memory it does not own. |
