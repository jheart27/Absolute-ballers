# Online multiplayer — post-v1 milestone (NOT implemented)

Flagged per the brief: v1 ships local-only, but the sim is shaped for
rollback-friendly online play over **Steamworks P2P via GodotSteam**.

## What v1 already guarantees

- **Intents are the wire format.** Every pawn is driven exclusively by
  `PlayerIntent` (a handful of bools + a Vector2) — a remote player is just
  a controller whose intents arrive over the network instead of from
  `Input`. AI pawns stay host-side controllers producing the same structs.
- **Fixed-order step function.** `MatchScene._physics_process` runs
  coordinators -> intents -> ballers -> ball -> clock in a stable order at a
  fixed 60Hz tick; sim state lives in plain fields (`MatchState`, Baller and
  GameBall sim vars), separate from rendering, so it can be snapshotted.
- **Single RNG stream.** All gameplay randomness goes through
  `MatchScene.rng` — seed it from the host and outcomes replicate.
- **Rendering is read-only.** Visual nodes never mutate sim state, so
  re-simulated ticks (rollback) or interpolated remote state need no
  visual-side changes.

## Remaining work (the actual milestone)

1. Extract `Baller`/`GameBall` sim fields into serializable state structs
   (they are already plain data; this is mechanical).
2. Float determinism audit or (simpler) host-authoritative model: host
   simulates, clients send intents + render snapshots with interpolation.
   For a 2-4 player arcade game, host-authoritative + client-side
   prediction of your own pawn is the pragmatic pick.
3. GodotSteam lobby + P2P sessions (`lobby_created`/`p2p_session_request`),
   channel for intents (unreliable sequenced) + snapshots/events
   (reliable).
4. Join flow in TeamSelect (a network seat is just a seat whose device is a
   Steam ID), desync detection via periodic state hashes.
