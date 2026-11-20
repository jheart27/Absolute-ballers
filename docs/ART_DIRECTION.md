# Art direction — chibi rig

The character look: **chibi gacha style** (about 2 heads tall, big glossy eyes,
expressive faces), in the spirit of the SD sprites in NIKKE / Uma Musume.
Previews live in [`docs/art/`](art/):

| File | Shows |
|---|---|
| `cast_roster.png` | the five girls in their signature idle poses |
| `cast_portraits.png` | each girl's expression range |
| `expressions_aki.png` | the full expression set on one face |
| `moveset_aki.png` | dribble, jump shot, slam, block, steal, knockdown, celebrate, on fire |
| `animated_preview.gif` | run + dribble cycle, idle with blink, celebrate hop |

## Why a rig instead of pixel art

Pixel art is drawn per frame, per character (about 450 frames for the roster),
and doesn't generate well procedurally. A **cutout rig** (the Spine /
gacha battle-sprite technique) draws each body part once and animates with math:

- **Bones + forward kinematics** for the body and legs.
- **Stretchy 2-bone IK** for arms, so hands land on the ball whatever the pose.
- **Hair chains** that lag behind motion (ponytail, twintails, long hair).
- **A layered face**: eyes, mouth, brows and anime FX marks are separate
  layers, so an expression is just a different combination.
- **One rig, one pose set, one expression set for the whole cast.** A new girl
  is a data entry, not new animation work.

## The tool

`tools/chibi_rig/chibi_rig.py` (pure Python + Pillow; renders at 4x and
downsamples for clean lineart):

```
python3 tools/chibi_rig/chibi_rig.py showcase docs/art          # regenerate all previews
python3 tools/chibi_rig/chibi_rig.py one yumi dribble joy out.png  # one character/pose/face
```

Rendering style: gradient fills, cel shadows (light from the upper-left),
occlusion shadows (under bangs, chin and hems), colored lineart, glossy
zigzag hair shine, and a dark sticker stroke around the whole silhouette so
characters pop on any court.

## Adding things

- **A character**: add an entry to `CAST` with hair/eye/kit colors, `skin`
  (`fair`/`tan`), `style` (`ponytail`, `twintails`, `bob`, `long`, `buns`),
  `bangs` (`default`, `blunt`, `swept`, `spiky`), `acc` (`scrunchie`,
  `ribbons`, `clip`, `flower`, `headband`), `tilt` (eye shape: `+` sharp /
  tsurime, `-` gentle / tareme), jersey `number`, `ahoge`, signature `idle`
  pose and `signature` expression.
- **An expression**: add an entry to `EXPR` combining eyes (`open`, `happy`,
  `blink`, `smug`, `angry`, `surprised`, `sparkle`, `teary`, `squeeze`,
  `dizzy`, or a `(near, far)` pair for winks), a mouth (`smile`, `open`,
  `grin`, `shout`, `o`, `O`, `cat`, `smirk`, `pout`, `frown`, `wavy`,
  `tongue`), brows (`neutral`, `up`, `worried`, `angry`, `determined`) and
  FX marks (`blush_lines`, `sparkles`, `sweat`, `anger`, `stars`, `tears`).
- **A pose**: add a branch to `make_pose`. Poses are bone angles plus
  optional IK targets (`ik_n` / `ik_f` = target, elbow bend direction, max
  stretch). Pass `t` in `[0, 1)` for looping animations.

## Getting this into the game (next milestone)

The game still renders the old placeholder sprite sheets. The plan is to
**bake** rig animations into sprite sheets that follow the existing contract
in `scripts/match/baller_anim.gd`: same row order and animation names, but a
larger frame size to match the detail of the chibi art. Since the game only
sees sheets, the swap needs no gameplay changes, only new frame-size constants
and camera tuning. Expressions can be baked per animation (focus on the jump
shot, fired up while on fire, dizzy when knocked down).
