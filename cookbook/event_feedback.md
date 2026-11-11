# Sound and effects on a game event

**Goal**: a sound, a particle effect and a camera shake when something happens in the match (a push, a hit, a goal).
**From**: the sandbox sample's push (`samples/sandbox`).

The simulation doesn't play sounds. It writes a **tick event**, and the feedback table maps event kinds to sounds, effects, shake and flashes. No view code is needed per event.

## 1. Name the event kind

Event kinds are a `MEALKIT_ENUM`, so the editor's [Feedback] panel can list them by name:

% from: samples/sandbox/sim/World.h
```cpp
MEALKIT_ENUM(EventKind, u8, Push, Bounce, Spawn, Fall, Jump, Impact, Countdown, MatchStart, MatchEnd, RoundEnd);
```

## 2. Push the event in the simulation

Where the thing happens, push one event with who did it, where, and one value:

% from: samples/sandbox/sim/Commands.cpp
```cpp
            world.events.push(makeEvent(EventKind::Push, c.player, pawn->position, world.tuning.pushRadius));
```

Events are cleared every tick and aren't part of the state, so they don't change the hash.

## 3. Map it in the feedback table

`assets/feedback.table` (the editor's [Feedback] panel) says what each kind does. A row named after the kind applies to everyone; `Push.local` applies only to the player who did it:

% from: samples/sandbox/assets/feedback.table
```text
row Push
sound push
effect spark
shake 0.12
shakeSeconds 0.2
shakeRange 14
```

`sound push` is an event in `assets/sounds.events` (made in MkAudio) and `effect spark` is `assets/effects/spark.fx`. The game's `GameSession` already passes every tick event to the table with `ctx.feedback.trigger`, so a new event needs only steps 1 to 3.
