# Absolute Ballers

2D retro pixel-art arcade basketball in the spirit of NBA Jam: exaggerated
physics, big dunks, shot-timing meter, and the "SHE'S ON FIRE!" streak.
Original anime-styled ballers, 3v3 full court by default (1v1 / 2v2 / 5v5
selectable from the main menu — team size is pure data).

Built with **Godot 4.3+** and GDScript. No third-party addons required.

## Running it

1. Open the project folder in Godot 4.3 or newer (first open imports the
   placeholder PNGs — let it finish).
2. Press F5. Boot -> main menu -> EXHIBITION or TOURNAMENT.

All current art is generated programmer art (see below) — final AI-generated
pixel-art sheets drop in without code changes.

## Controls

| Action | Keyboard | Gamepad |
| --- | --- | --- |
| Move | WASD / arrows | Left stick / d-pad |
| Shoot / Block (context) | K or Space | A |
| Pass / Steal (context) | J | B |
| Turbo | L or Shift | X or right trigger |
| Switch to nearest teammate | I | Y |
| Pause | Esc / P | Start |

Context rules (NBA Jam classic): with the ball, SHOOT jumps and charges the
meter — release at the apex for a perfect shot; near the rim it becomes a
dunk. On defense the same button is a block jump, and PASS becomes a steal
swipe (hold TURBO while swiping to shove — knockdowns are legal here).

**Local multiplayer:** 2-4 humans (keyboard + up to 3 pads, or 4 pads). In
SQUAD SELECT every device presses SHOOT to join a seat, picks a side and a
baller, and locks in. Remaining roster slots are AI-filled.

## Match rules

- 4 quarters x 2:00 by default (configurable in the menu), sudden-death OT.
- No fouls, no free throws, no out-of-bounds. Goaltending welcome.
- Shot clock optional (off by default).
- **On fire:** 3 consecutive personal buckets ignites a baller — speed and
  shot boosts, aura, unlimited turbo — until the other team scores or she
  burns out (4 baskets). A per-TEAM fire variant can be toggled in the menu.

## Repository layout

```
assets/placeholder/   generated programmer art (characters, court, fx)
data/characters/      one .tres per baller — stats, sprite sheet path
data/teams/           one .tres per franchise — name, colors
docs/                 design decisions, architecture, asset + Steam notes
scenes/               boot.tscn (screens are built in code for now)
scripts/
  core/               autoloads (EventBus, Game, input), settings, config
  data/               CharacterDef / TeamDef / roster loading
  match/              the whole on-court sim + visuals + HUD + camera
  ai/                 TeamAI coordinator (marks, spacing, difficulty)
  tournament/         single-elimination bracket state
  steam/              GodotSteam scaffold + achievement stubs
  ui/                 main menu, squad-select lobby, bracket screen
tools/                generate_placeholders.py (regenerates all art)
```

## Placeholder art pipeline

`python3 tools/generate_placeholders.py` (needs Pillow) regenerates every
sprite. The character sheet contract (frame size, row order, frame counts)
lives in `scripts/match/baller_anim.gd` and `docs/ASSET_PIPELINE.md` —
final art that follows it is a drop-in replacement.

## Roadmap

1. ~~Project scaffold~~ ✅
2. ~~Vertical slice: movement, ball physics, shot meter, scoring, camera~~ ✅
3. ~~Full team AI, full court, configurable team size~~ ✅
4. ~~On fire + announcer popups~~ ✅
5. ~~Local multiplayer (multi-gamepad lobby)~~ ✅
6. ~~Tournament bracket~~ ✅
7. ~~Steam scaffolding (stubs)~~ ✅
8. Post-v1: **online multiplayer** via GodotSteam P2P — architecture notes
   in `docs/ONLINE_MULTIPLAYER.md`; sound + music pass; real art drop-in;
   polish (tip-off, half-court switch, goaltend swats mid-flight).
