#!/usr/bin/env python3
"""Generate programmer-art placeholder sprites for Absolute Ballers.

Output goes to assets/placeholder/. Final AI-generated pixel art replaces
these files 1:1 — as long as it follows the sheet contract below, no code
changes are needed (see docs/ASSET_PIPELINE.md).

CHARACTER SHEET CONTRACT (must match scripts/match/baller_anim.gd):
  - frame size 96x96, grid of 6 columns x 9 rows, PNG with alpha
  - character faces RIGHT; feet touch y=88 inside the frame
  - rows, in order: idle(4), run(6), dribble(6), jump_shot(4), dunk(6),
    block(4), steal(4), hurt(4), celebrate(4)
  - unused cells in a row stay fully transparent

COURT PROJECTION: the court/hoop art is painted through the same low-angle
projection as scripts/core/court_geometry.gd (DEPTH_SCALE / X_SCALE_FAR /
X_SCALE_NEAR). If you change those constants, change them here too and
regenerate.

Usage: python3 tools/generate_placeholders.py
"""

import math
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "placeholder")

FRAME = 96
COLS = 6
CX = 48        # figure center x inside a frame
FEET = 88      # feet baseline y inside a frame
ROWS = [  # (name, frame count) — order is the contract
    ("idle", 4),
    ("run", 6),
    ("dribble", 6),
    ("jump_shot", 4),
    ("dunk", 6),
    ("block", 4),
    ("steal", 4),
    ("hurt", 4),
    ("celebrate", 4),
]

# --- projection, mirroring CourtGeometry ---
DEPTH_SCALE = 0.62
X_SCALE_FAR = 0.88
X_SCALE_NEAR = 1.06
HALF_DEPTH = 260.0


def proj(x, y, cx, cy):
    t = (y + HALF_DEPTH) / (HALF_DEPTH * 2.0)
    xs = X_SCALE_FAR + (X_SCALE_NEAR - X_SCALE_FAR) * t
    return (cx + x * xs, cy + y * DEPTH_SCALE)


# --- palettes ---
OUT_C = (38, 26, 46, 255)
SKIN = (255, 214, 178, 255)
SKIN_SH = (222, 172, 136, 255)
JERSEY = (240, 240, 246, 255)
JERSEY_SH = (203, 203, 218, 255)
TRIM = (94, 92, 116, 255)
SHORTS = (72, 68, 92, 255)
SHORTS_HI = (96, 92, 120, 255)
MOUTH = (196, 90, 100, 255)
BLUSH = (255, 168, 160, 200)

# id, hair RGB, hairstyle (bob | ponytail | twintails | long)
CHARACTERS = [
    ("aki", (214, 54, 66), "ponytail"),
    ("yumi", (76, 116, 235), "twintails"),
    ("rin", (52, 46, 62), "bob"),
    ("hana", (243, 126, 185), "long"),
    ("sora", (64, 194, 189), "bob"),
    ("miko", (238, 202, 96), "ponytail"),
    ("kaede", (154, 86, 205), "long"),
    ("nao", (238, 134, 66), "bob"),
    ("tsuki", (206, 210, 226), "long"),
    ("rei", (96, 184, 96), "twintails"),
]


def shade(c, k):
    return (max(0, min(255, int(c[0] * k))),
            max(0, min(255, int(c[1] * k))),
            max(0, min(255, int(c[2] * k))), 255)


def limb(d, p1, p2, color, w):
    """Thick line with round caps."""
    d.line([p1, p2], fill=color, width=w)
    r = max(1, w // 2)
    for p in (p1, p2):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)


def limb_o(d, p1, p2, color, w):
    """Outlined limb: dark silhouette then fill."""
    limb(d, p1, p2, OUT_C, w + 2)
    limb(d, p1, p2, color, w)


def bent(d, p1, p2, bend, color, w, outline=True):
    """Two-segment limb with a joint offset (knee/elbow)."""
    mid = ((p1[0] + p2[0]) / 2 + bend[0], (p1[1] + p2[1]) / 2 + bend[1])
    if outline:
        limb(d, p1, mid, OUT_C, w + 2)
        limb(d, mid, p2, OUT_C, w + 2)
    limb(d, p1, mid, color, w)
    limb(d, mid, p2, color, w)
    return mid


def poly_o(d, pts, fill, outline=OUT_C):
    d.polygon(pts, fill=fill, outline=outline)


# ---------------------------------------------------------------- the rig
def default_pose():
    return {
        "hip": (CX, 57.0), "shoulder": (CX, 37.0), "head": (CX, 24.0),
        "footL": (CX - 7, FEET), "footR": (CX + 7, FEET),
        "kneeL": (0, 0), "kneeR": (0, 0),
        "handL": (CX - 12, 54.0), "handR": (CX + 12, 54.0),
        "elbowL": (-2, 0), "elbowR": (2, 0),
        "lean": 0.0, "on_floor": False,
    }


def pose_for(row, f):
    p = default_pose()
    if row == "idle":
        bob = [0, 1, 1.5, 1][f]
        sway = [0, 0.6, 0, -0.6][f]
        for k in ("hip", "shoulder", "head"):
            p[k] = (p[k][0] + sway, p[k][1] + bob)
        p["handL"] = (CX - 11, 56 + bob)
        p["handR"] = (CX + 11, 56 + bob)
    elif row in ("run", "dribble"):
        a = f / 6.0 * math.tau
        s, c = math.sin(a), math.cos(a)
        lean = 4.0
        p["lean"] = lean
        p["hip"] = (CX + lean * 0.4, 56 - abs(s) * 1.5)
        p["shoulder"] = (CX + lean, 36 - abs(s) * 1.5)
        p["head"] = (CX + lean + 1, 23 - abs(s) * 1.5)
        p["footR"] = (CX + 6 + 15 * s, FEET - max(0.0, 11 * c))
        p["footL"] = (CX + 6 - 15 * s, FEET - max(0.0, -11 * c))
        p["kneeR"] = (5 + 3 * s, -3)
        p["kneeL"] = (5 - 3 * s, -3)
        if row == "run":
            p["handR"] = (CX + 6 - 13 * s, 50 - 4 * s)
            p["handL"] = (CX + 6 + 13 * s, 50 + 4 * s)
            p["elbowR"] = (4, 2)
            p["elbowL"] = (-4, 2)
        else:  # dribble: right hand pumps the ball, left guards
            p["handR"] = (CX + 15, 62 + 7 * s)
            p["elbowR"] = (5, -2)
            p["handL"] = (CX - 9, 48)
            p["elbowL"] = (-5, 0)
    elif row == "jump_shot":
        crouch = [8, 0, 0, 2][f]
        rise = [0, 5, 8, 4][f]
        p["hip"] = (CX, 57 + crouch - rise)
        p["shoulder"] = (CX, 37 + crouch - rise)
        p["head"] = (CX, 24 + crouch - rise)
        if f == 0:
            p["kneeL"] = (-6, -2)
            p["kneeR"] = (6, -2)
            p["handL"] = (CX - 6, 46)
            p["handR"] = (CX + 10, 46)
        else:
            spread = [0, 3, 4, 2][f]
            p["footL"] = (CX - 6 - spread, FEET - rise * 0.4)
            p["footR"] = (CX + 6 + spread, FEET - rise * 0.7)
            p["kneeR"] = (4, -2)
            up = [0, 16, 26, 22][f]
            p["handR"] = (CX + 5, 46 - up)
            p["elbowR"] = (6, -3)
            p["handL"] = (CX - 4, 50 - up * 0.8)
            p["elbowL"] = (-5, -2)
    elif row == "dunk":
        t = f / 5.0
        lean = 5 - 8 * t
        p["lean"] = lean
        rise = [0, 2, 5, 8, 6, 2][f]
        p["hip"] = (CX + lean * 0.4, 56 - rise)
        p["shoulder"] = (CX + lean, 36 - rise)
        p["head"] = (CX + lean + 1, 23 - rise)
        p["footL"] = (CX - 9 - 4 * t, FEET - rise * 0.8)
        p["footR"] = (CX + 3, FEET - 4 - rise)
        p["kneeL"] = (-5, -4)
        p["kneeR"] = (7, -6)
        # both hands: windup behind head -> slam forward-down
        arc = [(-2, -14), (2, -22), (0, -30), (10, -32), (18, -22), (20, -12)][f]
        p["handR"] = (CX + arc[0] + 6, 40 + arc[1])
        p["handL"] = (CX + arc[0] - 4, 42 + arc[1])
        p["elbowR"] = (8, -4)
        p["elbowL"] = (-6, -4)
    elif row == "block":
        stretch = [0, 5, 8, 3][f]
        p["hip"] = (CX, 56 - stretch * 0.6)
        p["shoulder"] = (CX, 36 - stretch)
        p["head"] = (CX, 23 - stretch)
        p["footL"] = (CX - 9, FEET - stretch * 0.5)
        p["footR"] = (CX + 9, FEET - stretch * 0.8)
        p["handL"] = (CX - 7, 8 - stretch * 0.5)
        p["handR"] = (CX + 7, 6 - stretch * 0.5)
        p["elbowL"] = (-2, 0)
        p["elbowR"] = (2, 0)
    elif row == "steal":
        lunge = [0, 6, 11, 5][f]
        p["lean"] = 8
        p["hip"] = (CX + lunge, 60)
        p["shoulder"] = (CX + lunge + 9, 42)
        p["head"] = (CX + lunge + 12, 30)
        p["footL"] = (CX - 10, FEET)
        p["footR"] = (CX + lunge + 8, FEET)
        p["kneeR"] = (4, -5)
        p["handR"] = (CX + lunge + 26, 46)
        p["elbowR"] = (4, -2)
        p["handL"] = (CX + lunge - 8, 50)
        p["elbowL"] = (-4, 2)
    elif row == "hurt":
        if f < 2:
            tip = [6, 14][f]
            p["lean"] = -tip
            p["hip"] = (CX - tip * 0.5, 58 + tip * 0.3)
            p["shoulder"] = (CX - tip, 40 + tip * 0.5)
            p["head"] = (CX - tip - 3, 28 + tip * 0.7)
            p["handL"] = (CX - tip - 12, 30)
            p["handR"] = (CX - tip + 12, 26)
            p["footR"] = (CX + 12, FEET - tip * 0.4)
        else:
            p["on_floor"] = True
    elif row == "celebrate":
        hop = [0, 6, 1, 6][f]
        p["hip"] = (CX, 56 - hop)
        p["shoulder"] = (CX, 36 - hop)
        p["head"] = (CX, 23 - hop)
        p["footL"] = (CX - 8, FEET - hop)
        p["footR"] = (CX + 8, FEET - hop - (4 if f % 2 else 0))
        p["kneeR"] = (3, -3) if f % 2 else (0, 0)
        p["handL"] = (CX - 15, 12 - hop)
        p["handR"] = (CX + 15, 12 - hop)
        p["elbowL"] = (-5, 2)
        p["elbowR"] = (5, 2)
    return p


def draw_hair_back(d, head, hair, style, lean=0.0):
    hx, hy = head
    base, dark = hair, shade(hair, 0.68)
    if style == "long":
        poly_o(d, [(hx - 10, hy - 6), (hx + 8, hy - 6), (hx + 6, hy + 26),
                   (hx - 12, hy + 26)], dark)
    elif style == "ponytail":
        tail = [(hx - 9 - lean, hy - 4), (hx - 5 - lean, hy - 8),
                (hx - 8 - lean * 1.5, hy + 20), (hx - 14 - lean * 1.5, hy + 18)]
        poly_o(d, tail, dark)
    elif style == "twintails":
        for sx in (-1, 1):
            poly_o(d, [(hx + sx * 12, hy - 4), (hx + sx * 8, hy - 7),
                       (hx + sx * (14 + abs(lean)), hy + 18),
                       (hx + sx * (18 + abs(lean)), hy + 14)], dark)


def draw_head(d, head, hair, style):
    hx, hy = head
    base, hi, dark = hair, shade(hair, 1.28), shade(hair, 0.68)
    # face
    d.ellipse([hx - 9, hy - 8, hx + 9, hy + 9], fill=SKIN, outline=OUT_C)
    # hair: full top-of-head coverage with a scalloped fringe
    d.pieslice([hx - 10, hy - 10, hx + 10, hy + 10], 180, 360, fill=base, outline=OUT_C)
    for tx in (hx - 5, hx + 1, hx + 6):
        d.polygon([(tx - 3, hy - 1), (tx + 3, hy - 1), (tx, hy + 3)], fill=base)
    # side locks framing the face
    poly_o(d, [(hx - 10, hy - 3), (hx - 7, hy - 3), (hx - 8, hy + 9),
               (hx - 11, hy + 7)], base)
    if style in ("bob", "long"):
        poly_o(d, [(hx + 7, hy - 3), (hx + 10, hy - 3), (hx + 11, hy + 7),
                   (hx + 8, hy + 9)], base)
    # shine streak
    d.arc([hx - 8, hy - 9, hx + 8, hy + 5], 210, 320, fill=hi, width=2)
    # eye (facing right): lashes, white, small iris with a shine
    d.line([hx + 1, hy - 1, hx + 7, hy - 1], fill=OUT_C, width=2)
    d.rectangle([hx + 2, hy, hx + 6, hy + 4], fill=(252, 252, 255, 255))
    d.rectangle([hx + 4, hy + 1, hx + 5, hy + 4], fill=dark)
    d.point((hx + 4, hy + 1), fill=(255, 255, 255, 255))
    # nose, mouth, blush
    d.point((hx + 8, hy + 3), fill=SKIN_SH)
    d.line([hx + 3, hy + 7, hx + 5, hy + 7], fill=MOUTH)
    d.point((hx - 2, hy + 5), fill=BLUSH)
    d.point((hx - 3, hy + 5), fill=BLUSH)


def draw_figure(d, p, hair, style, accent):
    """Painter for one frame. Draw order: back hair, back limbs, torso,
    front limbs, head. Crop-top jersey + shorts + long legs, tasteful."""
    if p["on_floor"]:
        # knocked flat on her back
        limb_o(d, (CX - 20, FEET - 6), (CX + 2, FEET - 8), JERSEY, 9)
        limb_o(d, (CX + 2, FEET - 7), (CX + 16, FEET - 4), SKIN, 5)  # legs out
        limb_o(d, (CX + 4, FEET - 10), (CX + 20, FEET - 12), SKIN, 5)
        d.ellipse([CX - 30, FEET - 13, CX - 16, FEET - 1], fill=SKIN, outline=OUT_C)
        poly_o(d, [(CX - 32, FEET - 12), (CX - 16, FEET - 14),
                   (CX - 14, FEET - 6), (CX - 30, FEET - 2)], shade(hair, 0.8))
        limb_o(d, (CX - 14, FEET - 8), (CX - 2, FEET - 14), SKIN, 4)  # arm flop
        return
    hip, sho, head = p["hip"], p["shoulder"], p["head"]
    draw_hair_back(d, head, hair, style, p["lean"])
    # back arm + back leg (left side is far side when facing right)
    bent(d, (sho[0] - 5, sho[1] + 2), p["handL"], p["elbowL"], SKIN_SH, 4)
    bent(d, (hip[0] - 4, hip[1]), p["footL"], p["kneeL"], SKIN_SH, 5)
    d.ellipse([p["footL"][0] - 5, p["footL"][1] - 4, p["footL"][0] + 4,
               p["footL"][1] + 2], fill=shade(accent, 0.75), outline=OUT_C)
    # hips / shorts
    poly_o(d, [(hip[0] - 8, hip[1] - 3), (hip[0] + 8, hip[1] - 3),
               (hip[0] + 9, hip[1] + 7), (hip[0] - 9, hip[1] + 7)], SHORTS)
    d.line([hip[0] - 8, hip[1] - 2, hip[0] + 8, hip[1] - 2], fill=SHORTS_HI, width=2)
    # bare midriff between shorts and crop jersey
    poly_o(d, [(hip[0] - 6, hip[1] - 8), (hip[0] + 6, hip[1] - 8),
               (hip[0] + 8, hip[1] - 2), (hip[0] - 8, hip[1] - 2)], SKIN)
    # crop-top jersey
    poly_o(d, [(sho[0] - 8, sho[1] - 2), (sho[0] + 8, sho[1] - 2),
               (hip[0] + 7, hip[1] - 7), (hip[0] - 7, hip[1] - 7)], JERSEY)
    d.line([sho[0] - 7, sho[1] + 8, sho[0] + 7, sho[1] + 8], fill=JERSEY_SH, width=2)
    d.line([hip[0] - 6, hip[1] - 8, hip[0] + 6, hip[1] - 8], fill=TRIM, width=2)
    d.line([sho[0] - 8, sho[1] - 1, sho[0] + 8, sho[1] - 1], fill=TRIM, width=2)
    # chest hint (one shaded line, kept tasteful)
    d.line([sho[0] - 3, sho[1] + 5, sho[0] + 4, sho[1] + 5], fill=JERSEY_SH, width=1)
    # front leg with sneaker + sock
    bent(d, (hip[0] + 4, hip[1] + 1), p["footR"], p["kneeR"], SKIN, 5)
    fr = p["footR"]
    d.line([fr[0] - 2, fr[1] - 6, fr[0] + 2, fr[1] - 6], fill=(245, 245, 250, 255), width=2)
    d.ellipse([fr[0] - 5, fr[1] - 4, fr[0] + 6, fr[1] + 2], fill=accent, outline=OUT_C)
    # front arm
    bent(d, (sho[0] + 5, sho[1] + 2), p["handR"], p["elbowR"], SKIN, 4)
    # neck + head
    limb(d, (head[0], head[1] + 7), (sho[0], sho[1] + 1), SKIN, 4)
    draw_head(d, head, hair, style)


def make_character_sheet(char_id, hair_rgb, style):
    hair = hair_rgb + (255,)
    accent = shade(hair, 1.1)
    img = Image.new("RGBA", (FRAME * COLS, FRAME * len(ROWS)), (0, 0, 0, 0))
    for r, (row_name, count) in enumerate(ROWS):
        for f in range(count):
            cell = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
            draw_figure(ImageDraw.Draw(cell), pose_for(row_name, f), hair,
                        style, accent)
            img.paste(cell, (f * FRAME, r * FRAME))
    img.save(os.path.join(OUT, "characters", f"{char_id}.png"))


# ---------------------------------------------------------------- fx bits
def make_fire_aura():
    frames = 4
    size = 128
    img = Image.new("RGBA", (size * frames, size), (0, 0, 0, 0))
    for f in range(frames):
        cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        for i in range(16):
            a = i / 16.0 * math.tau
            r = 40 + 5 * math.sin(a * 3 + f * 1.7)
            x, y = 64 + r * math.cos(a), 84 + r * 0.42 * math.sin(a)
            h = 14 + 11 * ((i * 7 + f * 3) % 5) / 4.0
            col = (255, 196, 44, 175) if (i + f) % 2 else (255, 94, 22, 175)
            d.polygon([(x - 5, y), (x + 5, y), (x, y - h)], fill=col)
        img.paste(cell, (size * f, 0))
    img.save(os.path.join(OUT, "fx", "fire_aura.png"))


def make_ball():
    img = Image.new("RGBA", (16 * 4, 16), (0, 0, 0, 0))
    for f in range(4):
        cell = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        d.ellipse([2, 2, 13, 13], fill=(244, 119, 46, 255), outline=(90, 40, 10, 255))
        d.ellipse([4, 4, 9, 9], outline=(255, 160, 90, 255))
        ang = f * math.pi / 4
        x1, y1 = 8 + 5 * math.cos(ang), 8 + 5 * math.sin(ang)
        x2, y2 = 8 - 5 * math.cos(ang), 8 - 5 * math.sin(ang)
        d.line([x1, y1, x2, y2], fill=(90, 40, 10, 255))
        img.paste(cell, (16 * f, 0))
    img.save(os.path.join(OUT, "fx", "ball.png"))


def make_markers():
    ring = Image.new("RGBA", (56, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.ellipse([2, 2, 53, 21], outline=(255, 255, 255, 230), width=3)
    d.ellipse([5, 5, 50, 18], outline=(255, 255, 255, 90), width=1)
    ring.save(os.path.join(OUT, "fx", "ring.png"))

    arrow = Image.new("RGBA", (18, 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(arrow)
    d.polygon([(1, 1), (16, 1), (9, 12)], fill=(255, 255, 255, 255),
              outline=(40, 30, 55, 255))
    arrow.save(os.path.join(OUT, "fx", "arrow.png"))

    shadow = Image.new("RGBA", (48, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    d.ellipse([1, 1, 46, 16], fill=(10, 5, 20, 105))
    shadow.save(os.path.join(OUT, "fx", "shadow.png"))


def make_hoop():
    """Perspective hoop, 192x480. Floor at the bottom edge; rim center at
    pixel (RIM_PX) = (96, 180), i.e. 300px above the floor — must match
    Hoop.RIM_PX / CourtGeometry.RIM_HEIGHT. Drawn as the LEFT-court hoop
    (rim reaching right, toward center court)."""
    w, h = 192, 480
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pole = (128, 128, 146, 255)
    pole_hi = (168, 168, 188, 255)
    pole_sh = (92, 92, 110, 255)
    # base + pole with padding
    d.polygon([(10, 480), (54, 480), (48, 460), (16, 460)], fill=(60, 58, 76, 255))
    d.rectangle([24, 120, 40, 462], fill=pole)
    d.line([26, 120, 26, 462], fill=pole_hi, width=3)
    d.line([38, 120, 38, 462], fill=pole_sh, width=3)
    d.rectangle([20, 300, 44, 388], fill=(206, 60, 74, 255))  # pad
    d.line([22, 302, 22, 386], fill=(238, 104, 116, 255), width=3)
    # angled arm to the board
    d.polygon([(36, 128), (70, 116), (70, 128), (36, 140)], fill=pole)
    # backboard (slight trapezoid = perspective) + glass shine
    d.polygon([(66, 78), (114, 88), (114, 208), (66, 218)], fill=(228, 235, 242, 255))
    d.polygon([(66, 78), (114, 88), (114, 94), (66, 84)], fill=(250, 253, 255, 255))
    d.line([(66, 78), (114, 88), (114, 208), (66, 218), (66, 78)],
           fill=(52, 44, 70, 255), width=3)
    d.line([(74, 120), (104, 126), (104, 172), (74, 166), (74, 120)],
           fill=(214, 72, 84, 255), width=3)  # shooter square
    # rim: flattened ellipse seen at a low angle
    d.ellipse([96, 170, 160, 190], fill=(238, 116, 34, 255), outline=(120, 48, 12, 255))
    d.ellipse([104, 174, 152, 184], fill=(0, 0, 0, 0), outline=(255, 164, 96, 255))
    d.line([98, 182, 158, 182], fill=(180, 74, 20, 255), width=2)
    # net: tapering mesh
    top_xs = [100 + i * 10 for i in range(7)]
    bot_xs = [114 + i * 6 for i in range(7)]
    for i in range(7):
        d.line([top_xs[i], 186, bot_xs[6 - i], 236], fill=(244, 246, 252, 215))
        d.line([top_xs[i], 186, bot_xs[i], 236], fill=(226, 228, 240, 190))
    d.arc([112, 228, 152, 244], 0, 180, fill=(244, 246, 252, 215), width=2)
    img.save(os.path.join(OUT, "court", "hoop.png"))


# ---------------------------------------------------------------- arena
def make_court():
    """Projected low-angle court, 2304x1024, origin at image center.
    Floor is a perspective trapezoid; area above the floor stays transparent
    so the parallax crowd layer shows behind it."""
    w, h = 2304, 1024
    cx, cy = w // 2, h // 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def pp(x, y):
        return proj(x, y, cx, cy)

    # apron slab
    poly = [pp(-1010, -302), pp(1010, -302), pp(1010, 302), pp(-1010, 302)]
    d.polygon(poly, fill=(62, 44, 78, 255))
    # hardwood planks as perspective quads
    x0 = -1010
    i = 0
    while x0 < 1010:
        x1 = min(x0 + 64, 1010)
        tone = 10 if i % 2 else 0
        d.polygon([pp(x0, -300), pp(x1, -300), pp(x1, 300), pp(x0, 300)],
                  fill=(203 - tone, 143 - tone, 80 - tone, 255))
        x0 = x1
        i += 1
    # subtle far-side darkening (fake distance light falloff)
    d.polygon([pp(-1010, -300), pp(1010, -300), pp(1010, -140), pp(-1010, -140)],
              fill=(40, 24, 30, 40))

    line = (246, 241, 236, 255)

    def pline(points, width=4):
        d.line([pp(x, y) for (x, y) in points], fill=line, width=width, joint="curve")

    def circle_pts(cx_w, cy_w, r, a0=0.0, a1=math.tau, steps=48):
        return [(cx_w + r * math.cos(a0 + (a1 - a0) * i / steps),
                 cy_w + r * math.sin(a0 + (a1 - a0) * i / steps))
                for i in range(steps + 1)]

    # boundary + half-court line + circles
    pline([(-880, -260), (880, -260), (880, 260), (-880, 260), (-880, -260)])
    pline([(0, -260), (0, 260)])
    pline(circle_pts(0, 0, 100))
    d.line([pp(x, y) for (x, y) in circle_pts(0, 0, 40)],
           fill=(240, 110, 30, 255), width=4, joint="curve")
    for side in (-1, 1):
        hx = 780 * side
        # painted key
        kx0, kx1 = side * 880, side * (880 - 280)
        d.polygon([pp(kx0, -110), pp(kx1, -110), pp(kx1, 110), pp(kx0, 110)],
                  fill=(164, 66, 50, 255))
        pline([(kx0, -110), (kx1, -110), (kx1, 110), (kx0, 110), (kx0, -110)])
        # free-throw circle + three-point arc (clipped to the floor)
        pline(circle_pts(side * (880 - 280), 0, 70))
        a = math.asin(min(1.0, 258.0 / 440.0))
        if side < 0:
            pline(circle_pts(hx, 0, 440, -a, a, 40))
        else:
            pline(circle_pts(hx, 0, 440, math.pi - a, math.pi + a, 40))
    # near-side skirt: dark fade from the floor edge to the bottom of canvas
    top = pp(0, 302)[1]
    d.rectangle([0, top, w, h], fill=(28, 18, 40, 255))
    d.rectangle([0, top, w, top + 8], fill=(90, 66, 110, 255))  # lit edge
    d.text((cx - 66, cy - 10), "ABSOLUTE BALLERS", fill=(122, 76, 46, 255))
    img.save(os.path.join(OUT, "court", "court_full.png"))


def make_crowd():
    """Parallax crowd layer, 2304x900. Bottom edge = arena wall that meets
    the far floor edge. Rendered behind the court, scrolled slower by
    MatchScene for depth."""
    rnd = random.Random(27)
    w, h = 2304, 900
    img = Image.new("RGBA", (w, h), (16, 10, 26, 255))
    d = ImageDraw.Draw(img)
    # haze gradient at the top
    for y in range(0, 220):
        k = y / 220.0
        d.line([0, y, w, y], fill=(int(16 + 14 * k), int(10 + 8 * k), int(26 + 18 * k), 255))
    # tiered stands: far rows small/dim, near rows bigger/brighter
    palette = [(96, 74, 116), (134, 104, 92), (74, 94, 126), (156, 134, 104),
               (108, 64, 86), (64, 64, 96), (150, 90, 90), (90, 120, 100)]
    rows = 9
    for r in range(rows):
        t = r / (rows - 1.0)
        row_y = 240 + int(t * 560)
        size = 3 + int(t * 5)
        step = size + 3
        dim = 0.45 + 0.55 * t
        # riser behind the row
        d.rectangle([0, row_y - size * 3, w, row_y + 2],
                    fill=(int(30 + 26 * t), int(20 + 16 * t), int(42 + 30 * t), 255))
        x = rnd.randrange(0, step)
        while x < w:
            if rnd.random() < 0.86:
                c = rnd.choice(palette)
                body = (int(c[0] * dim), int(c[1] * dim), int(c[2] * dim), 255)
                skin_t = rnd.choice([(238, 200, 170), (204, 160, 128), (166, 122, 92)])
                head = (int(skin_t[0] * dim), int(skin_t[1] * dim), int(skin_t[2] * dim), 255)
                d.rectangle([x, row_y - size, x + size, row_y + 2], fill=body)
                hs = max(2, size - 2)
                d.ellipse([x + 1, row_y - size - hs, x + 1 + hs, row_y - size], fill=head)
            x += step + rnd.randrange(0, 3)
    # arena wall + rail + banners
    d.rectangle([0, h - 74, w, h], fill=(52, 38, 74, 255))
    d.rectangle([0, h - 74, w, h - 68], fill=(150, 140, 180, 255))
    banners = [(0.2, 0.9, 1.0), (1.0, 0.55, 0.75), (0.55, 0.35, 0.9), (1.0, 0.85, 0.2),
               (0.9, 0.2, 0.25), (0.2, 0.8, 0.7), (0.85, 0.65, 0.25), (0.7, 0.4, 1.0)]
    bw = 150
    for i, c in enumerate(banners * 2):
        x = 40 + i * (bw + 44)
        if x + bw > w - 20:
            break
        col = (int(c[0] * 130), int(c[1] * 130), int(c[2] * 130), 255)
        d.rectangle([x, h - 60, x + bw, h - 14], fill=col)
        d.rectangle([x, h - 60, x + bw, h - 52], fill=(int(c[0] * 190), int(c[1] * 190),
                                                       int(c[2] * 190), 255))
    img.save(os.path.join(OUT, "court", "crowd.png"))


def main():
    for sub in ("characters", "court", "fx"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for char_id, hair, style in CHARACTERS:
        make_character_sheet(char_id, hair, style)
    make_fire_aura()
    make_ball()
    make_markers()
    make_hoop()
    make_court()
    make_crowd()
    print(f"placeholders written to {OUT}")


if __name__ == "__main__":
    main()
