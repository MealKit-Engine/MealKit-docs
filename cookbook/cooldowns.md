# Cooldowns and timers

**Goal**: an action that can be used again only after some seconds (a shove, a dash, a spell), or anything that happens "N seconds later".
**From**: the co-op sample's shove (`samples/coop`).

A timer in the simulation is a `mealkit::sim::TickTimer` (`mealkit/sim/TickTimer.h`): it stores the tick it becomes ready on, so it is one number in the state, saved in snapshots and included in the hash. Never count real time in `sim/`.

## 1. Put the timer in the state

The timer belongs to the object that has the cooldown, declared like any other state field:

% from: samples/coop/sim/World.h
```cpp
    MEALKIT_FIELD(TickTimer, shove, {}, "밀치기 재사용");      // heroes
```

## 2. Put the length in tuning

How long the cooldown lasts is a game rule, so it goes in `Tuning` as `mealkit::Ticks`. The file and the editor's [Tuning] panel show seconds; the simulation gets ticks:

% from: samples/coop/sim/Tuning.h
```cpp
    MEALKIT_FIELD(mealkit::Ticks, shoveCooldown, mealkit::Ticks::seconds(1.5f), "밀치기 재사용 대기 (초)");
```

## 3. Check and start it

`ready(tick)` is true once the timer has run out (or was never started); `start(tick, ticks)` starts it again:

% from: samples/coop/sim/Pawns.cpp
```cpp
            if (intent.shove && p->shove.ready(s.tick)) {
                p->shove.start(s.tick, t.shoveCooldown.value);
                shove(world, *p, player);
            }
```

The same timer works for "N seconds later": start it when the thing begins, and act on the first tick where it is ready. For a countdown the player sees, the view reads `remaining(tick)` from the state and divides by the tick rate.
