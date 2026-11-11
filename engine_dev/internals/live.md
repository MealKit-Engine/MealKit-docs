# Live

This page explains the live connection server: how it finds its port, what it writes for tools, how requests and the state stream are handled.
`live` comes after `data` and before the view side in the layer order: it uses only `core`, `platform` and `net`, and the folders that add services (`game`, `editor`) come later. What tools see is specified in {doc}`../../reference/tool_contract`. The code is in {engine}`engine/src/mealkit/live`.

## Starting

`live::Server::start(ServerConfig)` opens a non-blocking `net::TcpListener` on `127.0.0.1`:

- The editor asks for `live::kEditorPort` (27220) and the next nine, so tools find it on the same port between runs. If all are taken, or the game asks for port 0, the system picks a free port.
- The token is 128 random bits per run unless the config gives one (automated tests).
- With a project folder, it writes `build/live/<kind>-<pid>.json`. Before writing, it removes files whose process id is no longer running (`platform::processRunning`), left over from crashes. `stop()` (also the destructor) deletes its own file.

Who starts a server:

| Where | When | Kind |
|---|---|---|
| `game::runGame` (the game exe) | `MEALKIT_LIVE` is 1: development builds. `build.bat Export` passes `-DMEALKIT_LIVE=OFF` | `game` |
| `editor::Editor::setProject` | Every time a project opens | `editor` |

check.ps1 makes sure the exported exe does not contain the server.

## Requests

`update()` runs once per frame on the main thread. It accepts up to eight connections, reads what has arrived, and parses a request when the headers and `Content-Length` body are complete (64 MB at most). The response is written in pieces as the socket accepts it, then the connection closes. A quiet connection closes after 1800 frames.

`handle(method, path, origin, body)` does the routing and can be called without sockets (unit test `live_server`):

1. The path must start with `/<token>/`, otherwise 404.
2. If the rest starts with a service name, that service handles it with the path after the name and the query.
3. A browser `Origin` is accepted only if it is the server's own origin or the service's `allowOrigin` accepts it; otherwise 403. Requests from programs have no `Origin`.
4. `OPTIONS` answers the CORS preflight (with `Access-Control-Allow-Private-Network` when Chrome asks).
5. `api/hello` is built in.

Because services run on the main thread, they can change engine state without locks, as the background-work rule in {engine}`docs/CODING_MODEL.md` asks.

## State stream

`GET /<token>/api/events?topics=a,b` keeps the connection open with `Content-Type: text/event-stream`. `publish(topic, json)` appends `event: <topic>` and `data: <json>` to every connection that listens to the topic. `listening(topic)` lets the caller skip building JSON nobody reads. A connection that does not read is closed when 4 MB are waiting.
`addTopic` declares a topic for `api/hello` before anyone listens. The game and the editor declare `stats` and publish `game::FrameStats::json()` after each report period.
