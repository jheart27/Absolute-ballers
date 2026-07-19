# Architecture

## The input -> state -> render split

The whole sim is structured for the post-v1 online milestone:

```
HumanInput / AIInput  --produces-->  PlayerIntent  (one per baller per tick)
                                          |
MatchScene._physics_process (fixed order) v
  TeamAI.update -> poll intents -> switching -> Baller.sim -> Ball.sim -> clock
                                          |
BallerVisual / GameBall sprites  <--reads-- sim fields (never writes)
```

- **Input**: `PlayerIntent` is the only thing the sim consumes. Humans and
  AI are interchangeable per-pawn (`baller.controller`), which is also what
  makes SWITCH and control-follows-pass trivial. For netcode, intents are
  the structs that get serialized.
- **State**: `MatchState` (score/clock/fire/possession) is a plain
  RefCounted with no node access; Baller/Ball keep their sim data in plain
  fields updated inside `sim(delta)` called by MatchScene in a fixed order —
  one deterministic-friendly step function.
- **Render**: `BallerVisual`, ball sprites, HUD, camera only read sim state
  in `_process`. Killing every visual node would not change a match result
  (given the same RNG stream).

`EventBus` (autoload) carries gameplay facts (baskets, fire, steals) out to
HUD/announcer/Steam without the sim knowing they exist.

## World model

2.5D arcade space: `position` = (x along court, y depth), `z` = height,
screen pos = `(x, y - z)`, y-sorted by floor y. Constants in
`CourtGeometry` (1 unit = 1 px of court art; rims at x = ±780, z = 300).

Shots are resolved **at release** (`ShotResolver`: meter quality, distance,
stats, pressure, fire, block windows) and the ball flight animates the
predetermined outcome — the NBA Jam way. Misses turn into live rebounds;
there is no out-of-bounds and no stoppage: after a basket the scored-on
team inbounds instantly under its own hoop.

## App flow

`Game` (autoload) owns settings, roster, and screen switching:
boot.tscn -> MainMenu -> TeamSelect (lobby) -> MatchScene -> back, or
TeamSelect -> TournamentState/TournamentScreen -> MatchScene per round.
Screens are code-built Controls (no .tscn per screen yet — trivial to
migrate when a UI art pass happens).

## Data-driven roster

`data/characters/*.tres` (CharacterDef) and `data/teams/*.tres` (TeamDef)
are discovered at runtime by `Roster` — drop a file in, it's in the game.
Sprite sheet paths live only in CharacterDef; the sheet layout contract
lives only in `BallerAnim`. Gameplay code never touches an art path.

## AI layering

- `TeamAI` (one per team): defensive matchup assignment (ball handler
  covered first), offensive spacing slots, loose-ball chaser election, and
  the difficulty parameter table (think rate, release timing error, steal
  rate, block/shove urges).
- `AIInput` (one per baller): turns TeamAI guidance into intents — drive /
  dunk / open-shot / kick-out decisions with the ball, cuts off ball,
  guard-and-swipe on defense, apex-timed shot releases with
  difficulty-scaled error.
