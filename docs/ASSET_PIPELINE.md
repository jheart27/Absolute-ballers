# Asset pipeline — swapping in final art

All current art is programmer art from `tools/generate_placeholders.py`.
Final AI-generated pixel art replaces files 1:1; nothing in gameplay code
references an art path (paths live in `data/characters/*.tres`, layout in
`scripts/match/baller_anim.gd`).

## Character sheet contract (the important one)

- PNG with alpha, **6 columns x 9 rows of 96x96 frames** (576x864 total).
- Character faces **RIGHT** (the game flips for left). Feet touch **y=88**
  inside each frame.
- Rows in fixed order, with fixed frame counts (unused cells transparent):

| row | animation | frames | loops |
|----:|-----------|-------:|-------|
| 0 | idle | 4 | yes |
| 1 | run | 6 | yes |
| 2 | dribble | 6 | yes |
| 3 | jump_shot | 4 | no |
| 4 | dunk | 6 | no |
| 5 | block | 4 | no |
| 6 | steal | 4 | no |
| 7 | hurt | 4 | no |
| 8 | celebrate | 4 | yes |

FPS per row is code-side in `BallerAnim.ROWS` (tweak freely). If final art
needs a different frame size or counts, change the single table in
`BallerAnim` — every sheet must then follow the new contract.

To add a **new baller**: drop `name.png` following the contract anywhere
under `assets/`, copy any `data/characters/*.tres`, edit id/name/stats/
`sprite_sheet` path. Done — she appears in the lobby pool.

## Other art, all placeholder-replaceable in place

- `fx/fire_aura.png` — 4 frames of 96x96, drawn behind the sprite.
- `fx/ball.png` — 4 frames of 16x16 (rendered at 2x).
- `fx/ring.png`, `fx/arrow.png`, `fx/shadow.png` — tinted at runtime.
- `court/court_full.png` — 2304x1024, painted through the low-angle
  **projection** in `CourtGeometry` (DEPTH_SCALE / X_SCALE_FAR/NEAR). The
  sim stays in flat floor coords (x∈[-880,880], y∈[-260,260], rims at
  x=±780); rendering projects them. If you change the projection constants,
  change them in `tools/generate_placeholders.py` too and regenerate.
- `court/crowd.png` — 2304x900 parallax layer drawn *behind* the court and
  scrolled slower by MatchScene (CROWD_PARALLAX) for depth. Bottom edge =
  the arena wall/banners that meet the far sideline.
- `court/hoop.png` — 192x480 perspective hoop, drawn as the LEFT hoop (rim
  reaching right); rim center at pixel (128,180), floor at y=480
  (`Hoop.RIM_PX` if it moves).

Godot import: project defaults to nearest-neighbor filtering; first editor
open generates `.import` files — commit them.

## Audio

`tools/generate_audio.py` produces procedural placeholder SFX in
`assets/placeholder/audio/`. **Filenames are the contract** — AudioManager
loads by basename, so final sound design replaces the WAVs 1:1:

bounce, dribble, swish, rim_clank, slam, block, steal, whoosh, pass,
buzzer, fire_ignite, knockdown, click, cheer, crowd_loop (looped ambient
bed; loop points are set in code).

Any format Godot imports as an AudioStream works (.wav/.ogg — if you switch
to .ogg, update the extension filter in `audio_manager.gd`). Missing files
degrade to silence with a warning, never a crash.
