#!/usr/bin/env python3
"""Generate programmer-art placeholder sprites for Absolute Ballers.

Output goes to assets/placeholder/. Final AI-generated pixel art replaces
these files 1:1 — as long as it follows the sheet contract below, no code
changes are needed (see docs/ASSET_PIPELINE.md).

CHARACTER SHEET CONTRACT (must match scripts/match/baller_anim.gd):
  - frame size 64x64, grid of 6 columns x 9 rows, PNG with alpha
  - character faces RIGHT; feet touch y=60 inside the frame
  - rows, in order: idle(4), run(6), dribble(6), jump_shot(4), dunk(6),
    block(4), steal(4), hurt(4), celebrate(4)
  - unused cells in a row stay fully transparent

Usage: python3 tools/generate_placeholders.py
"""

import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "placeholder")

FRAME = 64
COLS = 6
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

SKIN = (245, 203, 160, 255)
JERSEY = (216, 216, 224, 255)   # neutral — team identity is a tinted floor ring in-game
SHORTS = (150, 150, 165, 255)
OUTLINE = (40, 30, 50, 255)

# id, hair RGB, hairstyle (bob | ponytail | twintails | long)
CHARACTERS = [
    ("aki", (210, 50, 60), "ponytail"),
    ("yumi", (70, 110, 230), "twintails"),
    ("rin", (45, 40, 55), "bob"),
    ("hana", (240, 120, 180), "long"),
    ("sora", (60, 190, 185), "bob"),
    ("miko", (235, 200, 90), "ponytail"),
    ("kaede", (150, 80, 200), "long"),
    ("nao", (235, 130, 60), "bob"),
    ("tsuki", (200, 205, 220), "long"),
    ("rei", (90, 180, 90), "twintails"),
]


def px(draw, x, y, w, h, color):
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=color)


def draw_head(d, cx, top, hair, style, tilt=0):
    """Head with hairstyle. cx = center x, top = top of head y."""
    # hair back layer
    if style == "long":
        px(d, cx - 8, top, 16, 22, hair)
    elif style == "ponytail":
        px(d, cx - 12 + tilt, top + 4, 5, 16, hair)
    elif style == "twintails":
        px(d, cx - 13 + tilt, top + 6, 4, 14, hair)
        px(d, cx + 9 + tilt, top + 6, 4, 14, hair)
    # face
    px(d, cx - 6, top + 3, 12, 11, SKIN)
    # hair top/fringe
    px(d, cx - 7, top, 14, 4, hair)
    px(d, cx - 7, top + 3, 3, 5, hair)
    px(d, cx + 4, top + 3, 3, 5, hair)
    if style == "bob":
        px(d, cx - 8, top + 2, 2, 10, hair)
        px(d, cx + 6, top + 2, 2, 10, hair)
    # eye (facing right)
    px(d, cx + 2, top + 7, 2, 2, OUTLINE)


def draw_body(d, cx, hip_y, lean=0, arm="down", legs=(0, 0), crouch=0):
    """Chunky torso/limbs. hip_y = waist line. legs = (front dy, back dy)."""
    torso_top = hip_y - 14 + crouch
    # legs (skin) — dy raises the foot for run cycles
    fdy, bdy = legs
    px(d, cx - 5 + lean, hip_y, 4, 12 - bdy, SKIN)      # back leg
    px(d, cx + 1 + lean, hip_y, 4, 12 - fdy, SKIN)      # front leg
    # shorts
    px(d, cx - 6 + lean, hip_y - 2, 12, 5, SHORTS)
    # jersey
    px(d, cx - 6 + lean, torso_top, 12, 12, JERSEY)
    px(d, cx - 6 + lean, torso_top, 12, 2, OUTLINE)     # collar accent
    # arms
    if arm == "down":
        px(d, cx - 8 + lean, torso_top + 2, 3, 10, SKIN)
        px(d, cx + 5 + lean, torso_top + 2, 3, 10, SKIN)
    elif arm == "up":  # both arms straight up (block / celebrate / dunk slam)
        px(d, cx - 8 + lean, torso_top - 10, 3, 12, SKIN)
        px(d, cx + 5 + lean, torso_top - 10, 3, 12, SKIN)
    elif arm == "shoot":  # one arm up, one bent
        px(d, cx + 4 + lean, torso_top - 12, 3, 14, SKIN)
        px(d, cx - 8 + lean, torso_top + 2, 3, 8, SKIN)
    elif arm == "reach":  # forward swipe (steal) / dribble hand
        px(d, cx + 5 + lean, torso_top + 4, 10, 3, SKIN)
        px(d, cx - 8 + lean, torso_top + 2, 3, 10, SKIN)
    elif arm == "cock":  # ball cocked behind head (dunk windup)
        px(d, cx - 2 + lean, torso_top - 10, 12, 3, SKIN)
        px(d, cx - 8 + lean, torso_top + 2, 3, 8, SKIN)
    return torso_top


def draw_pose(d, row, f, hair, style):
    """One 64x64 frame. Feet baseline y=60, facing right."""
    cx, feet = 32, 60
    if row == "idle":
        bob = [0, 1, 1, 0][f]
        hip = feet - 12 + bob
        t = draw_body(d, cx, hip, arm="down", crouch=bob)
        draw_head(d, cx, t - 16 + bob, hair, style)
    elif row in ("run", "dribble"):
        cyc = [(6, 0), (3, 3), (0, 6), (0, 6), (3, 3), (6, 0)][f]
        hip = feet - 12 + (1 if f % 3 == 1 else 0)
        arm = "reach" if row == "dribble" else "down"
        t = draw_body(d, cx, hip, lean=2, arm=arm, legs=cyc)
        draw_head(d, cx + 2, t - 16, hair, style, tilt=-2)
    elif row == "jump_shot":
        arm = ["down", "shoot", "shoot", "down"][f]
        crouch = [4, 0, 0, 2][f]
        hip = feet - 12 - [0, 6, 8, 2][f]
        t = draw_body(d, cx, hip, arm=arm, crouch=crouch, legs=(2, 2) if f in (1, 2) else (0, 0))
        draw_head(d, cx, t - 16 + crouch, hair, style)
    elif row == "dunk":
        arm = ["down", "cock", "cock", "up", "up", "down"][f]
        hip = feet - 12 - [2, 6, 10, 12, 8, 0][f]
        t = draw_body(d, cx, hip, lean=3, arm=arm, legs=(4, 1))
        draw_head(d, cx + 3, t - 16, hair, style, tilt=-2)
    elif row == "block":
        stretch = [0, 4, 6, 2][f]
        hip = feet - 12 - stretch
        t = draw_body(d, cx, hip, arm="up", legs=(2, 2))
        draw_head(d, cx, t - 16, hair, style)
    elif row == "steal":
        lunge = [0, 4, 7, 3][f]
        hip = feet - 10
        t = draw_body(d, cx + lunge - 3, hip, lean=4, arm="reach", crouch=3)
        draw_head(d, cx + lunge, t - 15, hair, style, tilt=-3)
    elif row == "hurt":
        if f < 2:  # falling backward
            tip = [4, 10][f]
            hip = feet - 12 + tip // 2
            t = draw_body(d, cx - tip, hip, lean=-tip // 2, arm="up")
            draw_head(d, cx - tip - 2, t - 15 + tip // 3, hair, style)
        else:  # flat on the floor
            px(d, cx - 14, feet - 7, 24, 6, JERSEY)
            px(d, cx + 8, feet - 8, 10, 7, SKIN)   # head
            px(d, cx + 10, feet - 10, 10, 4, hair)
            px(d, cx - 20, feet - 5, 7, 4, SKIN)   # arm flopped out
    elif row == "celebrate":
        hop = [0, 4, 0, 4][f]
        hip = feet - 12 - hop
        t = draw_body(d, cx, hip, arm="up", legs=(hop, hop))
        draw_head(d, cx, t - 16, hair, style)


def make_character_sheet(char_id, hair, style):
    img = Image.new("RGBA", (FRAME * COLS, FRAME * len(ROWS)), (0, 0, 0, 0))
    for r, (row_name, count) in enumerate(ROWS):
        for f in range(count):
            cell = Image.new("RGBA", (FRAME, FRAME), (0, 0, 0, 0))
            draw_pose(ImageDraw.Draw(cell), row_name, f, hair + (255,), style)
            img.paste(cell, (f * FRAME, r * FRAME))
    img.save(os.path.join(OUT, "characters", f"{char_id}.png"))


def make_fire_aura():
    """4 frames of 96x96 flame ring, additive-friendly, drawn behind the sprite."""
    frames = 4
    img = Image.new("RGBA", (96 * frames, 96), (0, 0, 0, 0))
    for f in range(frames):
        cell = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        for i in range(14):
            a = i / 14.0 * math.tau
            r = 30 + 4 * math.sin(a * 3 + f * 1.7)
            x, y = 48 + r * math.cos(a), 62 + r * 0.45 * math.sin(a)
            h = 10 + 8 * ((i * 7 + f * 3) % 5) / 4.0
            col = (255, 190, 40, 170) if (i + f) % 2 else (255, 90, 20, 170)
            d.polygon([(x - 4, y), (x + 4, y), (x, y - h)], fill=col)
        img.paste(cell, (96 * f, 0))
    img.save(os.path.join(OUT, "fx", "fire_aura.png"))


def make_ball():
    img = Image.new("RGBA", (16 * 4, 16), (0, 0, 0, 0))
    for f in range(4):
        cell = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(cell)
        d.ellipse([2, 2, 13, 13], fill=(244, 119, 46, 255), outline=(90, 40, 10, 255))
        ang = f * math.pi / 4
        x1, y1 = 8 + 5 * math.cos(ang), 8 + 5 * math.sin(ang)
        x2, y2 = 8 - 5 * math.cos(ang), 8 - 5 * math.sin(ang)
        d.line([x1, y1, x2, y2], fill=(90, 40, 10, 255))
        img.paste(cell, (16 * f, 0))
    img.save(os.path.join(OUT, "fx", "ball.png"))


def make_markers():
    ring = Image.new("RGBA", (48, 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    d.ellipse([2, 2, 45, 17], outline=(255, 255, 255, 220), width=3)
    ring.save(os.path.join(OUT, "fx", "ring.png"))

    arrow = Image.new("RGBA", (16, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(arrow)
    d.polygon([(1, 1), (14, 1), (8, 10)], fill=(255, 255, 255, 255))
    arrow.save(os.path.join(OUT, "fx", "arrow.png"))

    shadow = Image.new("RGBA", (40, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    d.ellipse([1, 1, 38, 14], fill=(10, 5, 20, 110))
    shadow.save(os.path.join(OUT, "fx", "shadow.png"))


def make_hoop():
    """Left-court hoop (rim extends right, toward center court). 128x400.
    Floor line is the bottom edge; rim center is at pixel (76, 100),
    i.e. 300px above the floor — matches CourtGeometry.RIM_HEIGHT."""
    img = Image.new("RGBA", (128, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pole = (120, 120, 135, 255)
    px(d, 16, 60, 8, 340, pole)                       # pole
    px(d, 12, 394, 24, 6, (90, 90, 105, 255))         # base
    px(d, 24, 64, 20, 6, pole)                        # arm to board
    px(d, 44, 30, 8, 110, (235, 240, 245, 255))       # backboard
    px(d, 44, 30, 8, 4, (200, 60, 60, 255))
    px(d, 44, 86, 8, 26, (200, 60, 60, 255))          # shooter square
    px(d, 46, 90, 4, 18, (235, 240, 245, 255))
    px(d, 52, 96, 48, 8, (240, 110, 30, 255))         # rim (center px x=76)
    for i in range(5):                                # net
        x = 54 + i * 10
        d.line([x, 104, 64 + i * 5, 134], fill=(240, 240, 250, 200))
    img.save(os.path.join(OUT, "court", "hoop.png"))


def make_court():
    """Full court + arena, 2048x1280. World origin = image center; 1 world
    unit = 1px. Playable floor: x in [-880, 880], y in [-260, 260]; rims at
    x = +/-780. The oversized canvas gives MatchCamera zoom-out headroom
    (MIN_ZOOM in match_camera.gd assumes these dimensions)."""
    import random

    w, h = 2048, 1280
    ox, oy = w // 2, h // 2
    img = Image.new("RGBA", (w, h), (24, 16, 36, 255))       # arena dark
    d = ImageDraw.Draw(img)
    # crowd: noisy pixel blobs outside the apron
    rnd = random.Random(27)
    for _ in range(9000):
        x, y = rnd.randrange(0, w), rnd.randrange(0, h)
        if abs(x - ox) < 1000 and abs(y - oy) < 400:
            continue
        c = rnd.choice([(90, 70, 110), (130, 100, 90), (70, 90, 120),
                        (150, 130, 100), (100, 60, 80), (60, 60, 90)])
        d.rectangle([x, y, x + 3, y + 3], fill=c + (255,))
    # apron
    d.rectangle([ox - 1000, oy - 400, ox + 1000, oy + 400], fill=(58, 40, 72, 255))
    # hardwood planks
    for i in range(ox - 1000, ox + 1000, 64):
        tone = 8 if (i // 64) % 2 else 0
        d.rectangle([i, oy - 300, min(i + 63, ox + 1000), oy + 300],
                    fill=(201 - tone, 141 - tone, 78 - tone, 255))
    line = (245, 240, 235, 255)
    lw = 4

    def rect_outline(x0, y0, x1, y1):
        d.rectangle([ox + x0, oy + y0, ox + x1, oy + y1], outline=line, width=lw)

    rect_outline(-880, -260, 880, 260)                       # boundary
    d.line([ox, oy - 260, ox, oy + 260], fill=line, width=lw)  # half court
    d.ellipse([ox - 100, oy - 100, ox + 100, oy + 100], outline=line, width=lw)
    d.ellipse([ox - 40, oy - 40, ox + 40, oy + 40], outline=(240, 110, 30, 255), width=lw)
    for side in (-1, 1):
        hx = 780 * side
        # painted key
        kx0, kx1 = side * 880, side * (880 - 280)
        d.rectangle([ox + min(kx0, kx1), oy - 110, ox + max(kx0, kx1), oy + 110],
                    fill=(160, 64, 48, 255), outline=line, width=lw)
        # free-throw circle
        fx = side * (880 - 280)
        d.ellipse([ox + fx - 70, oy - 70, ox + fx + 70, oy + 70], outline=line, width=lw)
        # three-point arc around the rim
        r = 440
        box = [ox + hx - r, oy - r, ox + hx + r, oy + r]
        if side < 0:
            d.arc(box, -68, 68, fill=line, width=lw)
        else:
            d.arc(box, 112, 248, fill=line, width=lw)
        # center-court logo hint
    d.text((ox - 60, oy - 12), "ABSOLUTE BALLERS", fill=(120, 70, 40, 255))
    img.save(os.path.join(OUT, "court", "court_full.png"))


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
    print(f"placeholders written to {OUT}")


if __name__ == "__main__":
    main()
