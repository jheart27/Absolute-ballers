"""Props: head accessories, the basketball, and effects layers drawn behind
the character (flames, speed lines, impact burst, swoosh)."""

import math

from PIL import Image, ImageFilter

from .geom import about, ap, apl, bez, capsule, catmull, ell, fluffy, mrot, offset_line, qbez, rell, strand
from .paint import C, Canvas, Grad
from .face import eye_params


# Where each accessory sits in the draw order:
#   back = behind the body (tied to tails), face = on the face under the bangs,
#   top  = over the hair.
ACC_STAGE = {"scrunchie": "back", "ribbons": "back", "glasses": "face", "bandaid": "face",
             "clip": "top", "flower": "top", "headband": "top", "bow": "top", "moon": "top"}


def rrect(cx, cy, w, h, r, n=6):
    """Rounded rectangle polygon."""
    pts = []
    for qx, qy, a0 in ((cx + w / 2 - r, cy - h / 2 + r, -math.pi / 2), (cx + w / 2 - r, cy + h / 2 - r, 0.0),
                       (cx - w / 2 + r, cy + h / 2 - r, math.pi / 2), (cx - w / 2 + r, cy - h / 2 + r, math.pi)):
        for i in range(n + 1):
            a = a0 + (math.pi / 2) * i / n
            pts.append((qx + r * math.cos(a), qy + r * math.sin(a)))
    return pts


def bow(cv, p, s, col, sh, ln, lw, ang=0.0):
    for sgn in (-1, 1):
        cv.shape(rell(p[0] + sgn * 0.88 * s, p[1] - 0.10 * s, 0.86 * s, 0.56 * s, sgn * 0.35 + ang, 24),
                 C(col), C(sh), C(ln), lw * 0.8, shift=0.25 * s)
        tail = [(p[0] + sgn * 0.15 * s, p[1]), (p[0] + sgn * 0.62 * s, p[1] + 1.10 * s),
                (p[0] + sgn * 0.30 * s, p[1] + 1.02 * s), (p[0] + sgn * 0.02 * s, p[1] + 0.30 * s)]
        cv.shape(tail, C(col), C(sh), C(ln), lw * 0.7, shift=0.2 * s)
    cv.shape(ell(p[0], p[1], 0.36 * s, 0.34 * s, n=20), C(col), C(sh), C(ln), lw * 0.8, shift=0.12 * s)


def _glasses(cv, X, g, pal, lw):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    frame, rims = C(pal["frame"]), []
    for which in ("near", "far"):
        c, w, h, _ = eye_params(which, hx, hy, R)
        rim = X(rrect(c[0] + w * 0.02, c[1] + h * 0.06, w * 1.30, h * 0.92, h * 0.30))
        cv.shape(rim, C(pal["lens"]), alpha=55)
        cv.shape(rim, None, None, frame, lw * 0.85)
        cv.polyline(X([(c[0] - w * 0.30, c[1] + h * 0.22), (c[0] - w * 0.04, c[1] - h * 0.16)]),
                    C((255, 255, 255)), R * 0.025, alpha=170, clip=[rim])
        rims.append((c, w, h))
    (nc, nw, nh), (fc, fw, fh) = rims
    a, b = (nc[0] + nw * 0.65, nc[1] - nh * 0.04), (fc[0] - fw * 0.65, fc[1] - fh * 0.06)
    cv.polyline(X(qbez(a, ((a[0] + b[0]) / 2, a[1] - 0.06 * R), b, 8)), frame, lw * 0.8)
    for e, dx in (((fc[0] + fw * 0.65, fc[1] - fh * 0.10), 0.14), ((nc[0] - nw * 0.65, nc[1] - nh * 0.04), -0.12)):
        cv.polyline(X([e, (e[0] + dx * R, e[1] - 0.03 * R)]), frame, lw * 0.8)


def _bandaid(cv, X, g, pal, lw):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    c = (hx - 0.50 * R, hy + 0.66 * R)
    tilt = about(c, -22.0)
    cv.shape(X(apl(tilt, rrect(c[0], c[1], 0.30 * R, 0.12 * R, 0.05 * R))), C(pal["bandage"]), None,
             C(pal["bandage_ln"]), lw * 0.55)
    cv.shape(X(apl(tilt, rrect(c[0], c[1], 0.10 * R, 0.08 * R, 0.02 * R))), C((255, 232, 210)))
    for dx in (-0.10, -0.075, 0.075, 0.10):
        dot = (c[0] + dx * R, c[1])
        cv.shape(X(apl(tilt, ell(dot[0], dot[1], 0.008 * R, 0.008 * R, n=8))), C(pal["bandage_ln"]))


def _moon(cv, X, g, pal, lw):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    cx, cy, r = hx + 0.66 * R, hy - 0.74 * R, 0.15 * R
    outer = ell(cx, cy, r, r, math.radians(60), math.radians(300), 24)
    inner = ell(cx + 0.42 * r, cy, 0.80 * r, 0.80 * r, math.radians(250), math.radians(110), 20)
    cv.shape(X(outer + inner), C(pal["gold"]), C(pal["gold_sh"]), C(pal["gold_ln"]), lw * 0.6, shift=0.03 * R)


def draw_accessory(cv, Mh, g, pal, P, ch, roots, stage):
    acc = ch["acc"]
    if ACC_STAGE.get(acc) != stage:
        return
    R, hx, hy, lw = g["R"], g["hx"], g["hy"], P["lw"]
    X = lambda pts: apl(Mh, pts)
    kit = (pal["jersey"], pal["jersey_sh"], pal["jersey_ln"])
    if acc == "scrunchie" and roots:
        r = roots[0]
        cv.shape(fluffy(r[0], r[1], 0.18 * R, 0.14 * R, 0, math.tau, 8, 0.10, n=64)[:-1],
                 C(kit[0]), C(kit[1]), C(kit[2]), lw * 0.9, shift=0.06 * R)
    elif acc == "ribbons":
        for r in roots:
            bow(cv, r, 0.20 * R, *kit, lw)
    elif acc == "bow":
        bow(cv, ap(Mh, (hx - 0.62 * R, hy - 0.86 * R)), 0.30 * R, *kit, lw, math.radians(mrot(Mh)) - 0.35)
    elif acc == "glasses":
        _glasses(cv, X, g, pal, lw)
    elif acc == "bandaid":
        _bandaid(cv, X, g, pal, lw)
    elif acc == "moon":
        _moon(cv, X, g, pal, lw)
    elif acc == "clip":
        cx, cy = hx - 0.52 * R, hy - 0.34 * R
        for a, b in (((-0.12, -0.06), (0.12, 0.06)), ((-0.12, 0.06), (0.12, -0.06))):
            cv.shape(X(capsule((cx + a[0] * R, cy + a[1] * R), 0.075 * R, (cx + b[0] * R, cy + b[1] * R), 0.075 * R)),
                     C(pal["gold"]), C(pal["gold_sh"]), C(pal["gold_ln"]), lw * 0.7, shift=0.02 * R)
    elif acc == "flower":
        cx, cy, r = hx + 0.66 * R, hy - 0.78 * R, 0.15 * R
        for i in range(5):
            a = -math.pi / 2 + i * math.tau / 5
            cv.shape(X(rell(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55, r * 0.46, r * 0.32, a, 20)),
                     C((255, 250, 252)), C((246, 196, 214)), C((186, 96, 130)), lw * 0.6, shift=0.04 * R)
        cv.shape(X(ell(cx, cy, r * 0.24, r * 0.24, n=14)), C((255, 214, 90)), None, C((176, 120, 40)), lw * 0.5)
    elif acc == "headband":
        line = catmull([(hx - 0.98 * R, hy - 0.40 * R), (hx - 0.40 * R, hy - 0.80 * R),
                        (hx + 0.30 * R, hy - 0.82 * R), (hx + 0.95 * R, hy - 0.46 * R)], n=10)
        band = X(strand(line, lambda t: 0.17 * R))
        cv.shape(band, C(kit[0]), C(kit[1]), C(kit[2]), lw * 0.85, shift=0.05 * R)
        cv.polyline(X(line), C(pal["trim"]), R * 0.03, clip=[band])


def draw_ball(cv, c, r, pal, lw, spin=0.0):
    """spin rotates the seams (degrees); shading and shine stay put."""
    body = ell(c[0], c[1], r, r, n=40)
    cv.shape(body, Grad(pal["ball_top"], pal["ball"], c[1] - r, c[1] + r * 0.4), C(pal["ball_sh"]),
             C(pal["ball_ln"]), lw, shift=r * 0.40)
    ln = C(pal["ball_ln"])
    S = about(c, spin)
    seams = [ell(c[0], c[1], r * 0.34, r, -math.pi / 2, math.pi / 2, 16),
             [(c[0] - r, c[1] + r * 0.05), (c[0], c[1] - r * 0.06), (c[0] + r, c[1] + r * 0.05)],
             ell(c[0] - r * 1.05, c[1], r * 0.62, r * 0.92, -1.1, 1.1, 14),
             ell(c[0] + r * 1.05, c[1], r * 0.62, r * 0.92, math.pi - 1.1, math.pi + 1.1, 14)]
    for seam in seams:
        cv.polyline(apl(S, seam), ln, lw * 0.55, clip=[body])
    cv.shape(ell(c[0] - r * 0.36, c[1] - r * 0.42, r * 0.26, r * 0.15, n=16), C((255, 240, 220)),
             clip=[body], alpha=170)


def flame(bx, by, wd, ht, lean):
    tip = (bx + lean, by - ht)
    pts = bez((bx - wd / 2, by), (bx - wd * 0.62, by - ht * 0.45), (bx + lean * 0.4 - wd * 0.2, by - ht * 0.78), tip, 14)
    pts += bez(tip, (bx + lean * 0.4 + wd * 0.26, by - ht * 0.70), (bx + wd * 0.62, by - ht * 0.40), (bx + wd / 2, by), 14)
    pts += ell(bx, by, wd / 2, wd * 0.28, 0, math.pi, 10)
    return pts


# (x offset, height, width, lean) per flame tongue, in rig units (u = R / 60)
FLAMES = ((-58, 130, 44, -14), (58, 140, 46, 16), (-32, 205, 54, -6), (34, 215, 56, 8),
          (0, 255, 66, 4), (-80, 90, 34, -20), (82, 96, 36, 20))


def draw_flames(cv, cx, base_y, u, phase=None):
    """The on-fire flames. phase=None: still; 0..1: flickering animation frame."""
    for i, (dx, ht, wd, lean) in enumerate(FLAMES):
        if phase is not None:
            wob = math.sin(phase * math.tau + i * 1.9)
            ht, lean = ht * (0.88 + 0.12 * wob), lean + 10 * math.sin(phase * math.tau * 2 + i)
        pts = flame(cx + dx * u, base_y, wd * u, ht * u, lean * u)
        cv.shape(pts, Grad((255, 70, 30), (255, 226, 110), base_y - ht * u, base_y), alpha=225)


def fx_layer(kind, w, h, g, P, char_img, anchor=None):
    """Effects that sit BEHIND the character (no sticker stroke)."""
    cv = Canvas(w, h)
    R, cx = g["R"], g["cx"]
    if kind == "fire":
        draw_flames(cv, cx, g["floor"] + 2, R / 60)
        img = cv.finish()
        glow_a = char_img.getchannel("A").filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, v * 2))
        glow = Image.new("RGBA", (w, h), (255, 150, 50, 0))
        glow.putalpha(glow_a)
        img.alpha_composite(glow)
        return img
    if kind == "speed":
        for i, (y, ln_, x0) in enumerate(((0.30, 110, 20), (0.42, 70, 50), (0.52, 130, 6), (0.64, 90, 30),
                                          (0.74, 60, 60), (0.84, 100, 14))):
            yy = h * y
            cv.polyline([(x0, yy), (x0 + ln_, yy)], C((255, 255, 255)), 2.4, alpha=110)
        return cv.finish()
    if kind == "burst" and anchor is not None:
        for i in range(14):
            a = i * math.tau / 14 + 0.2
            r0, r1 = R * 0.30, R * (0.62 + 0.22 * (i % 2))
            cv.polyline([(anchor[0] + r0 * math.cos(a), anchor[1] + r0 * math.sin(a)),
                         (anchor[0] + r1 * math.cos(a), anchor[1] + r1 * math.sin(a))],
                        C((255, 236, 140)), 3.0, alpha=230)
        return cv.finish()
    if kind == "swoosh" and anchor is not None:
        arc = ell(anchor[0] - R * 0.30, anchor[1] - R * 0.10, R * 0.70, R * 0.46, -0.2, 1.6, 20)
        cv.polyline(arc, C((255, 255, 255)), 5.0, alpha=150)
        cv.polyline(offset_line(arc, -R * 0.12), C((255, 255, 255)), 2.4, alpha=110)
        return cv.finish()
    return cv.finish()
