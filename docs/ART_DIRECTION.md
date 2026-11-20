# Art direction: the chibi rig

The character look is **chibi gacha style**: about 2 heads tall, big glossy
eyes, expressive faces, in the spirit of the SD sprites in NIKKE and Uma
Musume. Previews live in [`docs/art/`](art/):

| File | Shows |
|---|---|
| `cast_roster.png` | all ten girls in their signature idle poses |
| `cast_portraits.png` | each girl's expression range |
| `expressions_aki.png` | the full expression set on one face |
| `moveset_aki.png` | dribble, jump shot, slam, block, steal, knockdown, celebrate, on fire |
| `animated_preview.gif` | running dribble, idle with blink, celebration hop |
| `game_sprites.png` | the **baked game sprites** in two team colors, ball at its anchors, fire aura |

## Why a rig instead of pixel art

Pixel art is drawn per frame and per character, which comes to hundreds of
frames for the roster, and it doesn't generate well procedurally. A
**cutout rig** (the Spine / gacha battle-sprite technique) draws each body
part once and animates it with math:

- **Bones + forward kinematics** for the body and legs.
- **Stretchy 2-bone IK** for arms, so hands land on the ball whatever the pose.
- **Hair chains** that lag behind motion (ponytail, twintails, long hair).
- **A layered face.** Eyes, mouth, brows and anime FX marks are separate
  layers, so an expression is just a different combination.
- **One rig, one move set, one expression set for the whole cast.** A new
  girl is a data entry, not new animation work.

## The tool

`tools/chibi_rig/` is a pure Python package (Pillow, plus numpy for the bake).
It renders at 4x and downsamples for clean lineart. Run it from the repo root:

```
python3 -m tools.chibi_rig showcase docs/art           # regenerate all previews
python3 -m tools.chibi_rig one yumi dribble joy out.png  # one girl / move / face
python3 -m tools.chibi_rig bake                        # game sprite sheets (ASSET_PIPELINE.md)
```

Module map (each module imports only from the ones above it):

| Module | Job |
|---|---|
| `geom` | 2D math: bone transforms, curves, shape builders |
| `paint` | supersampled Canvas, colors, gradients, outlines |
| `cast` | the girls (`CAST`), palettes, team-kit grays, body proportions (`BODY`) |
| `rig` | skeleton, forward kinematics, stretchy arm IK |
| `body` | arms/hands, legs/sneakers, shorts, jersey, neck |
| `face` | eyes, mouths, brows, FX marks, expressions (`EXPR`) |
| `hair` | bangs, back hair, tails, buns, shine, ahoge |
| `props` | accessories, the ball, flames and effect layers |
| `poses` | every move as one function: bone angles + IK targets, keyframed |
| `render` | draws one girl in layer order and returns an RGBA image |
| `sheets` | showcase sheets for docs/art |
| `bake` | game sprite sheets + the generated `BallerSheet` contract |

Rendering style: gradient fills, cel shadows (light from the upper-left),
occlusion shadows (under bangs, chin and hems), colored lineart, glossy
zigzag hair shine, and a dark sticker stroke around the whole silhouette so
the girls pop on any court.

## Adding things

- **A girl**: add an entry to `CAST` (`cast.py`) with:
  - `hair` / `eyes` / `kit` colors (the kit is her showcase uniform; in the
    game she wears the team's)
  - `skin`: `fair`, `tan` or `deep`
  - `style`: `ponytail`, `twintails`, `bob`, `long`, `buns` or `short`
  - `bangs`: `default`, `blunt`, `swept` or `spiky`
  - `acc`: `scrunchie`, `ribbons`, `clip`, `flower`, `headband`, `glasses`,
    `bow`, `bandaid` or `moon`
  - `tilt`: eye shape, `+` sharp (tsurime) or `-` gentle (tareme)
  - jersey `number`, plus an `ahoge` flag
  - signature `idle` pose: `wave`, `peace`, `hip`, `cheer`, `fist`, `point`
    or `thumbs`. It doubles as her in-game celebration.
  - faces: `signature` (showcase), `face` (in-game default) and `cheer`
    (celebration)

  Then bake her (see ASSET_PIPELINE.md).
- **An expression**: add an entry to `EXPR` (`face.py`). Combine:
  - eyes: `open`, `happy`, `blink`, `smug`, `angry`, `surprised`, `sparkle`,
    `teary`, `squeeze` or `dizzy`, or a `(near, far)` pair for winks
  - a mouth: `smile`, `open`, `grin`, `shout`, `o`, `O`, `cat`, `smirk`,
    `pout`, `frown`, `wavy` or `tongue`
  - brows: `neutral`, `up`, `worried`, `angry` or `determined`
  - FX marks: `blush_lines`, `sparkles`, `sweat`, `anger`, `stars` or `tears`
- **A move**: write a function in `poses.py` and register it in `MOVES`. A
  move returns bone angles plus optional IK targets for each hand. An IK
  target names the body part it follows (`head`, `chest`, `hip`, `floor`,
  `sh_f`), so a hand stays on the ball or the cheek however the body moves.
  - Looping moves take `t` in `[0, 1)`.
  - One-shots are keyframed with `keyed()` over `t` from 0 to 1. Their
    timing is part of the game contract: `MARKS` pins the shot release and
    the slam.
  - `'ball': ('hand_f', along, across)` puts the ball on the hand, and the
    bake turns those positions into the game's ball anchors.

## In the game

The game draws the baked sheets with the team color applied by a shader
(see ASSET_PIPELINE.md). A girl stands about 160 px tall at camera zoom 1.

Each move has its own face:
- her own `face` while running and handling the ball
- focus on the jump shot
- shouting through the dunk and the block
- smug on the steal
- dizzy when knocked down
- her `cheer` face when celebrating

The fire is an aura strip drawn behind any move.
