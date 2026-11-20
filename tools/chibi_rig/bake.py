"""Bake the game's sprite sheets from the rig.

    python3 -m tools.chibi_rig bake [girl ...]      (all girls by default)

Per girl, two sheets with the same layout:
    assets/characters/<id>.png       the girl, team kit painted black
    assets/characters/<id>_kit.png   the team kit alone: rgb = gray shading, a = coverage
In the game, scripts/match/baller_kit.gdshader adds kit gray x team color on
top of the black kit, which is exactly what rendering the kit in the team
color would give, anti-aliased edges included. So any team color works and
every girl keeps her own hair, eyes, skin and accessories.

Also written: assets/fx/fire_aura.png and assets/fx/ball.png (strips), and
scripts/match/baller_sheet.gd: the GENERATED layout contract (frame size,
feet point, animation rows and timing, per-frame ball anchors) the game reads.

How the kit is separated: every frame renders three times with the kit
painted black (A), white (B) and in its gray shading (G). Compositing is
linear in the kit color, so in premultiplied color
    B - A = coverage * 255        G - A = coverage * gray
"""
import json
import math
import os
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .cast import BODY, CAST, KIT_GRAY, palette
from .paint import OUTLINE, Canvas, font
from .poses import MARKS
from .props import draw_ball, draw_flames
from .render import render

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHAR_DIR = os.path.join(ROOT, "assets", "characters")
FX_DIR = os.path.join(ROOT, "assets", "fx")
SHEET_GD = os.path.join(ROOT, "scripts", "match", "baller_sheet.gd")

SCALE = 0.56                 # rig -> game pixels (a girl stands ~160 px)
FRAME_W, FRAME_H = 176, 200  # one frame; FEET_X must stay FRAME_W / 2 so flip_h mirrors in place
FEET_X, FEET_Y = FRAME_W // 2, 188
RIG_FLOOR = FEET_Y - 4       # the rig's floor line sits a little above the sole bottoms
# Art bounds over every frame, measured with measure(): x -81..+74, y -180..+12
# from RIG_FLOOR, so the frame keeps >= 4 px of clear margin on every side.


def loop(n):
    return tuple(i / n for i in range(n))


# Rows in sheet order: (animation, move, variant, frame times, fps).
# fps 0 = one-shot whose frame the game picks from its own clock (sim state
# progress mapped onto move time t; see MARKS in poses.py).
ANIMS = [
    ("idle", "idle", "ready", loop(8), 8.0),
    ("run", "run", None, loop(8), 14.0),
    ("dribble", "dribble", None, loop(8), 14.0),
    ("hold", "hold", None, loop(8), 9.0),
    ("jump_shot", "jump_shot", None, (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.875, 1.0), 0.0),
    ("dunk", "dunk", None, (0.0, 0.12, 0.24, 0.36, 0.48, 0.6, 0.8, 1.0), 0.0),
    ("block", "block", None, (0.0, 0.2, 0.4, 0.6, 0.8, 1.0), 0.0),
    ("steal", "steal", None, tuple(i / 6 for i in range(7)), 0.0),
    ("hurt", "hurt", None, (0.0, 0.1, 0.22, 0.34, 0.5, 0.67, 0.83, 1.0), 0.0),
    ("celebrate", "celebrate", None, loop(8), 10.0),
]
COLUMNS = max(len(a[3]) for a in ANIMS)
AURA_FRAMES, AURA_FPS = 8, 12.0
BALL_FRAMES = 8
BALL_R = BODY["ball_r"] * SCALE
KIT_BASE = KIT_GRAY["jersey"][0] / 255.0   # kit gray that maps to exactly the team color


# ------------------------------------------------------------ one frame
def _frame(cid, move, variant, t, kit, info=None):
    return render(cid, move, t=t, variant=variant, scale=SCALE, w=FRAME_W, h=FRAME_H,
                  cx=FEET_X, floor=RIG_FLOOR, fx=False, shadow=False, ball=False, lift=False,
                  kit=kit, info=info, resample=Image.BOX)


def split_kit(black, white, gray):
    """Three kit passes -> (body with black kit, kit overlay), both RGBA uint8."""
    A = np.asarray(black, dtype=np.float32)
    B = np.asarray(white, dtype=np.float32)
    G = np.asarray(gray, dtype=np.float32)
    a = A[..., 3:4] / 255.0
    qa, qb, qg = A[..., :3] * a, B[..., :3] * a, G[..., :3] * a
    cover = np.clip((qb - qa).mean(axis=-1) / 255.0, 0.0, 1.0)   # 0..alpha
    lum = np.where(cover > 1e-4, (qg - qa).mean(axis=-1) / np.maximum(cover, 1e-4), 0.0)
    kit = np.zeros(A.shape, dtype=np.uint8)
    keep = cover >= 2.0 / 255.0
    kit[..., 0] = kit[..., 1] = kit[..., 2] = np.clip(lum, 0, 255).astype(np.uint8)
    kit[..., 3] = np.where(keep, np.round(cover * 255.0), 0).astype(np.uint8)
    return Image.fromarray(np.asarray(black, dtype=np.uint8)), Image.fromarray(kit)


def tint(body, kit, team):
    """What baller_kit.gdshader draws: body + kit gray x team color."""
    Bd = np.asarray(body, dtype=np.float32) / 255.0
    K = np.asarray(kit, dtype=np.float32) / 255.0
    col = np.minimum(K[..., :3] / KIT_BASE * (np.array(team, dtype=np.float32) / 255.0), 1.0)
    a = Bd[..., 3:4]
    rgb = (Bd[..., :3] * a + col * K[..., 3:4]) / np.maximum(a, 1e-4)
    out = np.concatenate([np.clip(rgb, 0, 1), a], axis=-1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8))


def kit_error(black, gray, kit):
    """Max premultiplied error of body + kit vs the true gray-kit render (0..255)."""
    A = np.asarray(black, dtype=np.float32)
    G = np.asarray(gray, dtype=np.float32)
    K = np.asarray(kit, dtype=np.float32)
    a = A[..., 3:4] / 255.0
    rebuilt = A[..., :3] * a + K[..., :3] * (K[..., 3:4] / 255.0)
    return float(np.abs(rebuilt - G[..., :3] * a).max())


def _bake_row(job):
    cid, row = job
    name, move, variant, times, _fps = ANIMS[row]
    bodies, kits, balls, worst, clipped = [], [], [], 0.0, []
    for i, t in enumerate(times):
        info = {}
        black = _frame(cid, move, variant, t, "black", info)
        white = _frame(cid, move, variant, t, "white")
        gray = _frame(cid, move, variant, t, "gray")
        body, kit = split_kit(black, white, gray)
        worst = max(worst, kit_error(black, gray, kit))
        al = np.asarray(body)[..., 3]
        if al[0, :].any() or al[-1, :].any() or al[:, 0].any() or al[:, -1].any():
            clipped.append("%s/%s#%d" % (cid, name, i))
        bodies.append(body)
        kits.append(kit)
        b = info.get("ball")
        balls.append(None if b is None else (round(b[0] - FEET_X, 1), round(b[1] - FEET_Y, 1)))
    return cid, row, bodies, kits, balls, worst, clipped


# ------------------------------------------------------------ the extras
def bake_aura(out):
    """Flicker strip drawn behind an on-fire girl, aligned to her feet."""
    strip = Image.new("RGBA", (FRAME_W * AURA_FRAMES, FRAME_H), (0, 0, 0, 0))
    for f in range(AURA_FRAMES):
        glow = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        top = FEET_Y - 150 * SCALE / 0.56
        ImageDraw.Draw(glow).ellipse([FEET_X - 46, top, FEET_X + 46, FEET_Y + 4], fill=(255, 140, 40, 120))
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        cv = Canvas(FRAME_W, FRAME_H)
        draw_flames(cv, FEET_X, RIG_FLOOR + 2, SCALE * 0.8, phase=f / AURA_FRAMES)
        glow.alpha_composite(cv.finish())
        strip.alpha_composite(glow, (f * FRAME_W, 0))
    strip.save(out, optimize=True)
    return out


def bake_ball(out):
    """Spinning ball strip for the game ball (same look as the rig's ball)."""
    size = int(math.ceil(BALL_R * 2 + 6))
    pal = palette("aki")
    strip = Image.new("RGBA", (size * BALL_FRAMES, size), (0, 0, 0, 0))
    for f in range(BALL_FRAMES):
        cv = Canvas(size, size)
        draw_ball(cv, (size / 2, size / 2), BALL_R, pal, BODY["lw"] * SCALE * 0.9, spin=f * 360 / BALL_FRAMES)
        cv.outline_pass(OUTLINE, BODY["stroke"] * SCALE)
        strip.alpha_composite(cv.finish(), (f * size, 0))
    strip.save(out, optimize=True)
    return out, size


# ------------------------------------------------------- the contract
def _gd(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 4))
    return repr(v)


def write_contract(balls, ball_frame):
    L = ['class_name BallerSheet',
         '## GENERATED by `python3 -m tools.chibi_rig bake` (tools/chibi_rig/bake.py).',
         '## Do not edit by hand: change the rig and re-bake.',
         '##',
         '## The layout every character sheet follows. Frames face RIGHT and the',
         '## FEET point of a frame is where she touches the floor. Each girl has two',
         '## sheets: <id>.png (team kit painted black) and <id>_kit.png (the kit in',
         '## gray), combined with the team color by baller_kit.gdshader.',
         '',
         'const FRAME_SIZE := Vector2i(%d, %d)' % (FRAME_W, FRAME_H),
         'const FEET := Vector2(%.1f, %.1f)' % (FEET_X, FEET_Y),
         'const COLUMNS := %d' % COLUMNS,
         'const BALL_RADIUS := %.2f  # assets/fx/ball.png: %d frames of %dx%d' % (
             BALL_R, BALL_FRAMES, ball_frame, ball_frame),
         'const AURA_FRAMES := %d  # assets/fx/fire_aura.png: frames the size of FRAME_SIZE' % AURA_FRAMES,
         'const AURA_FPS := %.1f' % AURA_FPS,
         'const KIT_BASE := %.4f  # kit gray that comes out as exactly the team color' % KIT_BASE,
         '',
         '## animation -> {',
         '##   row     sheet row',
         '##   fps     playback speed; 0 = one-shot the game scrubs from its own clock',
         '##   times   move time t (0..1) of each frame (see tools/chibi_rig/poses.py)',
         '##   mark    one-shots: the t the game syncs to (shot release, dunk slam)',
         '##   ball    ball center per frame as an offset from FEET, null = not in hand',
         '## }',
         'const ANIMS := {']
    for row, (name, move, _v, times, fps) in enumerate(ANIMS):
        L.append('\t"%s": {' % name)
        L.append('\t\t"row": %d,' % row)
        L.append('\t\t"fps": %s,' % _gd(float(fps)))
        L.append('\t\t"mark": %s,' % _gd(float(MARKS.get(move, 1.0))))
        L.append('\t\t"times": [%s],' % ", ".join(_gd(float(t)) for t in times))
        L.append('\t\t"ball": [')
        for b in balls[name]:
            L.append('\t\t\t%s,' % ("null" if b is None else "Vector2(%.1f, %.1f)" % b))
        L.append('\t\t],')
        L.append('\t},')
    L.append('}')
    with open(SHEET_GD, "w") as f:
        f.write("\n".join(L) + "\n")
    return SHEET_GD


# ------------------------------------------------------------ main
def bake(girls=None, procs=None):
    girls = girls or list(CAST)
    os.makedirs(CHAR_DIR, exist_ok=True)
    os.makedirs(FX_DIR, exist_ok=True)
    jobs = [(cid, row) for cid in girls for row in range(len(ANIMS))]
    sheets = {cid: (Image.new("RGBA", (FRAME_W * COLUMNS, FRAME_H * len(ANIMS)), (0, 0, 0, 0)),
                    Image.new("RGBA", (FRAME_W * COLUMNS, FRAME_H * len(ANIMS)), (0, 0, 0, 0))) for cid in girls}
    balls, worst, clipped = {}, 0.0, []
    with Pool(procs or os.cpu_count()) as pool:
        for cid, row, bodies, kits, row_balls, err, clip in pool.imap_unordered(_bake_row, jobs):
            body_sheet, kit_sheet = sheets[cid]
            for i, (b, k) in enumerate(zip(bodies, kits)):
                body_sheet.paste(b, (i * FRAME_W, row * FRAME_H))
                kit_sheet.paste(k, (i * FRAME_W, row * FRAME_H))
            name = ANIMS[row][0]
            if name in balls and balls[name] != row_balls:
                raise RuntimeError("ball anchors differ between girls in %s" % name)
            balls[name] = row_balls
            worst, clipped = max(worst, err), clipped + clip
    written = []
    for cid, (body_sheet, kit_sheet) in sheets.items():
        for img, suffix in ((body_sheet, ""), (kit_sheet, "_kit")):
            path = os.path.join(CHAR_DIR, cid + suffix + ".png")
            img.save(path, optimize=True)
            written.append(path)
    written.append(bake_aura(os.path.join(FX_DIR, "fire_aura.png")))
    ball_path, ball_frame = bake_ball(os.path.join(FX_DIR, "ball.png"))
    written.append(ball_path)
    written.append(write_contract(balls, ball_frame))
    print("kit split max error: %.2f / 255" % worst)
    if clipped:
        print("WARNING: art touches the frame edge in", ", ".join(sorted(clipped)))
    return written


PREVIEW_TEAMS = ((230, 51, 64), (51, 230, 255))   # Ronin red, Comets cyan (data/teams)


def preview(out):
    """docs/art/game_sprites.png: the baked sheets as the game draws them —
    team tint, ball at its anchor, fire aura — so the bake can be checked
    without opening Godot."""
    from .sheets import court_bg   # showcase helper; keeps the module map one-way
    with open(SHEET_GD) as f:
        anchors = _read_anchors(f.read())
    ball = Image.open(os.path.join(FX_DIR, "ball.png"))
    bs = ball.height
    aura = Image.open(os.path.join(FX_DIR, "fire_aura.png"))
    rows = [("aki", 0), ("rei", 1)]
    picks = [("idle", 0), ("run", 2), ("dribble", 0), ("hold", 2), ("jump_shot", 5), ("dunk", 5),
             ("block", 3), ("steal", 2), ("hurt", 7), ("celebrate", 3)]
    cols = max(len(CAST), len(picks))
    top, lab = 64, 26
    sheet = Image.new("RGBA", (FRAME_W * cols, top + 3 * (FRAME_H + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    d.text((16, 14), "In-game sprites as baked (%dx%d frames, team color applied by shader)" % (FRAME_W, FRAME_H),
           font=font(26), fill=(255, 214, 92, 255))
    names = [a[0] for a in ANIMS]

    def cell(cid, anim, f, team, x, y, fire=False):
        row = names.index(anim)
        box = (f * FRAME_W, row * FRAME_H, (f + 1) * FRAME_W, (row + 1) * FRAME_H)
        body = Image.open(os.path.join(CHAR_DIR, cid + ".png")).crop(box)
        kit = Image.open(os.path.join(CHAR_DIR, cid + "_kit.png")).crop(box)
        bg = court_bg(FRAME_W, FRAME_H, floor=FEET_Y)
        if fire:
            bg.alpha_composite(aura.crop((0, 0, FRAME_W, FRAME_H)))
        bg.alpha_composite(tint(body, kit, team))
        a = anchors[anim][f]
        if a is not None:
            bg.alpha_composite(ball.crop((0, 0, bs, bs)),
                               (int(round(FEET_X + a[0] - bs / 2)), int(round(FEET_Y + a[1] - bs / 2))))
        sheet.alpha_composite(bg, (x, y))

    y = top
    for i, cid in enumerate(CAST):
        cell(cid, "idle", 0, PREVIEW_TEAMS[i * 2 // len(CAST)], i * FRAME_W, y, fire=(cid == "rei"))
        d.text((i * FRAME_W + FRAME_W // 2, y + FRAME_H + 2), CAST[cid]["name"], font=font(18),
               fill=(232, 226, 255, 255), anchor="ma")
    for r, (cid, team) in enumerate(rows):
        y = top + (r + 1) * (FRAME_H + lab)
        for c, (anim, f) in enumerate(picks):
            cell(cid, anim, f, PREVIEW_TEAMS[team], c * FRAME_W, y)
            d.text((c * FRAME_W + FRAME_W // 2, y + FRAME_H + 2), anim.replace("_", " ").upper(), font=font(15),
                   fill=(200, 194, 226, 255), anchor="ma")
    sheet.convert("RGB").save(out)
    return out


def _read_anchors(gd):
    """Ball anchors back out of the generated contract (keeps preview honest)."""
    anchors, name = {}, None
    for line in gd.splitlines():
        s = line.strip()
        if s.endswith(": {") and s.startswith('"'):
            name = s.split('"')[1]
            anchors[name] = []
        elif name and s.startswith("Vector2("):
            x, y = s[len("Vector2("):].rstrip("),").split(",")
            anchors[name].append((float(x), float(y)))
        elif name and s == "null,":
            anchors[name].append(None)
    return anchors


def measure(girls=None):
    """Union of every frame's art bounds relative to the feet (sizing aid)."""
    girls = girls or list(CAST)
    lo, hi = [1e9, 1e9], [-1e9, -1e9]
    for cid in girls:
        for name, move, variant, times, _fps in ANIMS:
            for t in times:
                img = render(cid, move, t=t, variant=variant, scale=SCALE, w=400, h=400, cx=200, floor=360,
                             fx=False, shadow=False, ball=False, lift=False)
                bb = img.getbbox()
                if bb:
                    lo = [min(lo[0], bb[0] - 200), min(lo[1], bb[1] - 360)]
                    hi = [max(hi[0], bb[2] - 200), max(hi[1], bb[3] - 360)]
    print(json.dumps({"x": [lo[0], hi[0]], "y": [lo[1], hi[1]]}))
