# Asset pipeline

Nothing in gameplay code references an art path: character sheet paths live
in `data/characters/*.tres`, and the sheet layout lives in one generated
script, `scripts/match/baller_sheet.gd`.

## The girls: baked from the chibi rig

The characters, the ball and the fire aura are **baked** from the chibi rig
(see [ART_DIRECTION.md](ART_DIRECTION.md)). One command rebuilds them all,
together with the layout contract the game reads:

```
python3 -m tools.chibi_rig bake            # all girls (~1 min, needs Pillow + numpy)
python3 -m tools.chibi_rig bake aki rei    # just some
```

It writes:

| File | What |
|---|---|
| `assets/characters/<id>.png` | the girl, with her team kit painted **black** |
| `assets/characters/<id>_kit.png` | the kit alone, same layout: rgb = gray shading, alpha = coverage |
| `assets/fx/fire_aura.png` | on-fire flicker strip (frames the size of a character frame, same feet point) |
| `assets/fx/ball.png` | ball spin strip (square frames) |
| `scripts/match/baller_sheet.gd` | **GENERATED** contract: frame size, feet point, rows, timing, ball anchors |
| `docs/art/game_sprites.png` | preview of the sheets exactly as the game draws them |

The bake also checks that no art touches a frame edge, and that the kit
separation is exact. It prints the worst error, which should be about 1–2/255.

### Team colors

Every girl keeps her own hair, eyes, skin and accessories, while the uniform
takes the team color. `scripts/match/baller_kit.gdshader` adds
`kit gray x team color` on top of the black kit. Because compositing is
linear in the kit color, that equals rendering the kit in the team color,
anti-aliased edges included. The bake gets the two layers by rendering each
frame three times (kit in black, white and gray). Accessories drawn in kit
colors (Aki's scrunchie, Kaede's bow, Miko's headband, Yumi's and Rei's
ribbons) pick up the team color too. When both teams' colors are too alike,
`MatchScene` puts the away side in light "away whites" of its color.

### The contract (generated, never hand-edited)

- 176x200 frames, 8 columns, one row per animation. The girl faces **RIGHT**,
  and her feet are at `BallerSheet.FEET` (88, 188). Sprites use that point as
  their origin, so depth scaling and `flip_h` happen around where she stands.
- Rows: `idle, run, dribble, hold, jump_shot, dunk, block, steal, hurt, celebrate`.
- **Loops** (`fps > 0`) play on their own. **One-shots** (`fps 0`) are
  scrubbed by `BallerVisual` from the sim's clocks: frame `i` is the move at
  time `times[i]`, and `mark` is the moment the sim syncs to. The jump shot
  reaches its set point at the jump apex, and the dunk's slam frame lands
  as the sim scores. `Baller` aims the dunk with the slam frame's ball anchor,
  so the ball goes into the rim.
- `ball` lists the ball center per frame (offset from the feet), or `null`
  when it isn't in her hand. `GameBall` draws the held ball there, so it
  always meets the hand that's drawn. Dribble sounds fire when that ball
  touches the floor.

### Adding a girl

1. Add her to `CAST` in `tools/chibi_rig/cast.py` (see ART_DIRECTION.md).
2. `python3 -m tools.chibi_rig bake <id>`
3. Copy any `data/characters/*.tres`, then set the id, name, stats,
   `sprite_sheet` and `kit_sheet`. She appears in the lobby pool.

Changing moves, timing or frame counts happens in the rig (`poses.py`, plus
`ANIMS` in `bake.py`). Re-bake, and the game follows through `BallerSheet`.

## Arena art: placeholders, replaceable in place

`python3 tools/generate_placeholders.py` (Pillow) regenerates these files:

- `assets/placeholder/fx/ring.png`, `arrow.png`, `shadow.png`: tinted at runtime.
- `court/court_full.png`: 2304x1024, painted through the low-angle
  **projection** in `CourtGeometry` (DEPTH_SCALE / X_SCALE_FAR/NEAR). The
  sim stays in flat floor coords (x∈[-880,880], y∈[-260,260], rims at
  x=±780), and rendering projects them. If you change the projection
  constants, change them in `tools/generate_placeholders.py` too and
  regenerate.
- `court/crowd.png`: 2304x900 parallax layer, drawn *behind* the court and
  scrolled slower by MatchScene (CROWD_PARALLAX) for depth. Its bottom edge is
  the arena wall/banners that meet the far sideline.
- `court/hoop.png`: 192x480 perspective hoop, drawn as the LEFT hoop (rim
  reaching right). The rim center is at pixel (128,180) and the floor at
  y=480 (`Hoop.RIM_PX` if it moves).

Godot import and filtering: the project default is nearest-neighbor, for the
pixel-art arena. The baked girls, ball and aura are smooth illustration, so
their nodes set `TEXTURE_FILTER_LINEAR`. The first editor open generates the
`.import` files. `tools/` and `docs/` each hold a `.gdignore`, so the editor
doesn't import tooling or preview images.

## Audio

`tools/generate_audio.py` produces procedural placeholder SFX in
`assets/placeholder/audio/`. **Filenames are the contract.** AudioManager
loads sounds by basename, so final sound design replaces the WAVs 1:1:

bounce, dribble, swish, rim_clank, slam, block, steal, whoosh, pass,
buzzer, fire_ignite, knockdown, click, cheer, crowd_loop (looped ambient
bed; loop points are set in code).

Any format Godot imports as an AudioStream works (.wav/.ogg; if you switch
to .ogg, update the extension filter in `audio_manager.gd`). A missing file
degrades to silence with a warning, never a crash.
