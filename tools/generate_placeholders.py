#!/usr/bin/env python3
"""Generate programmer-art placeholders for the arena: court, crowd, hoop,
and the small FX markers (team ring, shadow, control arrow).

The girls, the ball and the fire aura are NOT made here any more: they are
baked from the chibi rig (python3 -m tools.chibi_rig bake), see
docs/ASSET_PIPELINE.md.

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


# ---------------------------------------------------------------- fx bits


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
    for sub in ("court", "fx"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    make_markers()
    make_hoop()
    make_court()
    make_crowd()
    print(f"placeholders written to {OUT}")


if __name__ == "__main__":
    main()
