# Rounds, countdown and match end

**Goal**: a match with a start countdown, timed rounds, a round winner and a match winner.
**From**: the sandbox sample's match (`samples/sandbox/sim/Match.cpp`).

The `matchflow` module (`matchflow/sim/MatchFlow.h`) keeps the phase (waiting, countdown, playing, round end, results) in the state and moves it forward every tick. The game only gives the rules and reacts to what the flow reports. It is a module, not part of every project: add it with `tools\module.ps1 add -Project <your project> matchflow` (until engine 0.9.8 it was the engine's `mealkit/sim/MatchFlow.h`).

## 1. Rules from tuning

The lengths and counts are tuning values (seconds in the file, ticks in `sim/`), turned into `MatchRules`:

% from: samples/sandbox/sim/Match.cpp
```cpp
    r.countdown = t.countdown.value;
    r.roundLength = t.roundLength.value;
    r.roundEndDelay = t.roundEndDelay.value;
    r.rounds = t.rounds;
    r.scoreLimit = t.scoreLimit;
```

## 2. Advance it every tick and react

`advanceMatch` moves the phase and returns what happened this tick. The game handles each event, for example resetting players at a round start and sending tick events for the view:

% from: samples/sandbox/sim/Match.cpp
```cpp
    handle(world, matchflow::advanceMatch(s.flow, world.rules, s.tick, players));
```

% from: samples/sandbox/sim/Match.cpp
```cpp
void handle(World& world, FlowEvent event) {
    switch (event) {
    case FlowEvent::RoundStart: onRoundStart(world); break;
    case FlowEvent::RoundEnd: onRoundEnd(world); break;
    case FlowEvent::MatchEnd: onMatchEnd(world); break;
```

## 3. Show the countdown

The view shouldn't guess when a number changes, so the simulation sends a tick event once per second of the countdown:

% from: samples/sandbox/sim/Match.cpp
```cpp
    if (s.flow.phase == MatchPhase::Countdown) { // 3, 2, 1
        const u32 left = s.flow.phaseEnd.remaining(s.tick);
        if (left > 0 && left % world.tickRate == 0)
            world.events.push(makeEvent(EventKind::Countdown, kNoPlayer, {}, static_cast<f32>(left / world.tickRate)));
    }
```

Scores live in the player slots in the state; the flow reads them through the rules (`scoreLimit`) and the game's `matchPlayers`. The results screen reads the same state.
