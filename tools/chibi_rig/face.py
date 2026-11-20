"""The face: outline, eyes (every state), mouths, brows, anime FX marks, and
the EXPR table that combines them into named expressions."""

import math

from .geom import about, apl, bez, catmull, ell, mm, qbez, star, strand
from .paint import C, Grad


def face_outline(hx, hy, R):
    """Round 'mochi' chibi face in 3/4 view facing right."""
    L0 = (hx - 0.95 * R, hy - 0.02 * R)
    L1 = (hx - 0.90 * R, hy + 0.52 * R)
    Cc = (hx + 0.14 * R, hy + 0.98 * R)
    Jw = (hx + 0.68 * R, hy + 0.70 * R)
    RC = (hx + 0.89 * R, hy + 0.28 * R)
    R0 = (hx + 0.91 * R, hy - 0.14 * R)
    pts = []
    pts += bez(L0, (hx - 1.00 * R, hy + 0.18 * R), (hx - 0.99 * R, hy + 0.38 * R), L1)
    pts += bez(L1, (hx - 0.80 * R, hy + 0.86 * R), (hx - 0.24 * R, hy + 1.00 * R), Cc)
    pts += bez(Cc, (hx + 0.44 * R, hy + 0.97 * R), (hx + 0.60 * R, hy + 0.86 * R), Jw)
    pts += bez(Jw, (hx + 0.80 * R, hy + 0.56 * R), (hx + 0.89 * R, hy + 0.42 * R), RC)
    pts += bez(RC, (hx + 0.92 * R, hy + 0.12 * R), (hx + 0.93 * R, hy - 0.02 * R), R0)
    c0 = (hx - 0.02 * R, hy - 0.08 * R)
    a0 = math.atan2(R0[1] - c0[1], R0[0] - c0[0])
    a1 = math.atan2(L0[1] - c0[1], L0[0] - c0[0]) - math.tau
    pts += ell(c0[0], c0[1], 0.94 * R, 0.96 * R, a0, a1, n=30)
    return pts


def eye_white(c, w, h):
    cx, cy = c
    top = bez((cx - w / 2, cy + h * 0.05), (cx - w * 0.40, cy - h * 0.52),
              (cx + w * 0.40, cy - h * 0.56), (cx + w / 2, cy - h * 0.02))
    bot = bez((cx + w / 2, cy - h * 0.02), (cx + w * 0.46, cy + h * 0.50),
              (cx - w * 0.44, cy + h * 0.54), (cx - w / 2, cy + h * 0.05))
    return top + bot


def eye_params(which, hx, hy, R):
    if which == "near":   # image-left, full width
        return (hx - 0.31 * R, hy + 0.30 * R), 0.43 * R, 0.53 * R, -1
    return (hx + 0.45 * R, hy + 0.29 * R), 0.31 * R, 0.51 * R, 1   # far, foreshortened


def lash_band(c, w, h, outer, th, n=20, cut=None):
    """Upper lash: thick band thickening toward the outer corner, with a flick.
    `cut` = (inner_y, outer_y) draws it along a lid line instead (smug/angry)."""
    if cut is None:
        edge = bez((c[0] - w * 0.5 - (w * 0.06 if outer < 0 else 0), c[1] + h * 0.10),
                   (c[0] - w * 0.40, c[1] - h * 0.55), (c[0] + w * 0.40, c[1] - h * 0.59),
                   (c[0] + w * 0.5 + (w * 0.06 if outer > 0 else 0), c[1] + h * 0.06), n=n)
    else:
        iy, oy = cut
        left_y, right_y = (iy, oy) if outer > 0 else (oy, iy)
        edge = qbez((c[0] - w * 0.56, left_y), (c[0], (left_y + right_y) / 2 - h * 0.08),
                    (c[0] + w * 0.56, right_y), n=n - 1)
    top = []
    for i, (x, y) in enumerate(edge):
        s = i / (len(edge) - 1) if outer > 0 else 1 - i / (len(edge) - 1)
        top.append((x, y - th * (0.28 + 0.72 * math.sin(min(1.0, s * 1.15) * math.pi / 2))))
    tip = edge[-1] if outer > 0 else edge[0]
    flick = (tip[0] + outer * w * 0.20, tip[1] - h * 0.18)
    poly = (edge + [flick] + top[::-1]) if outer > 0 else ([flick] + edge + top[::-1])
    return poly, edge, top


def draw_eye(cv, Mh, which, state, pal, g, lw, tilt):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    c, w, h, outer = eye_params(which, hx, hy, R)
    Me = mm(Mh, about(c, -outer * tilt * 9.0))   # tsurime (+) / tareme (-)
    X = lambda pts: apl(Me, pts)
    lash = C(pal["lash"])

    if state == "happy":   # ^ ^
        arc = bez((c[0] - w * 0.52, c[1] + h * 0.14), (c[0] - w * 0.26, c[1] - h * 0.40),
                  (c[0] + w * 0.26, c[1] - h * 0.40), (c[0] + w * 0.52, c[1] + h * 0.14), n=16)
        cv.polyline(X(arc + [(c[0] + w * 0.52, c[1] + h * 0.14)]), lash, R * 0.075)
        o = (c[0] + outer * w * 0.50, c[1] + h * 0.10)
        cv.polyline(X([o, (o[0] + outer * w * 0.18, o[1] - h * 0.10)]), lash, R * 0.045)
        return
    if state == "blink":   # calm closed
        arc = bez((c[0] - w * 0.50, c[1] + h * 0.06), (c[0] - w * 0.22, c[1] + h * 0.28),
                  (c[0] + w * 0.22, c[1] + h * 0.28), (c[0] + w * 0.50, c[1] + h * 0.06), n=16)
        cv.polyline(X(arc + [(c[0] + w * 0.50, c[1] + h * 0.06)]), lash, R * 0.065)
        o = (c[0] + outer * w * 0.50, c[1] + h * 0.06)
        cv.polyline(X([o, (o[0] + outer * w * 0.18, o[1] + h * 0.12)]), lash, R * 0.045)
        return
    if state == "squeeze":   # > <
        s = -outer
        pts = [(c[0] - s * w * 0.38, c[1] - h * 0.30), (c[0] + s * w * 0.34, c[1] + h * 0.02),
               (c[0] - s * w * 0.38, c[1] + h * 0.32)]
        cv.polyline(X(pts), lash, R * 0.072)
        return
    if state == "dizzy":   # @ @
        turns = 2.6
        steps = int(turns * math.tau / 0.12)
        sp = []
        for i in range(steps):
            t = i * 0.12
            k = 1 - t / (turns * math.tau)
            sp.append((c[0] + w * 0.46 * k * math.cos(t), c[1] + h * 0.42 * k * math.sin(t)))
        cv.polyline(X(sp), lash, R * 0.042)
        return

    # ---- open-eye family: open / surprised / sparkle / teary / smug / angry
    hh = h * (1.08 if state == "surprised" else 1.0)
    isc = 0.66 if state == "surprised" else 1.0
    wp = X(eye_white(c, w, hh))
    cv.shape(wp, C(pal["white"]), C(pal["eye_sh"]), shift=hh * 0.24, light=(0, 1))
    look = 0.17 if state == "smug" else 0.05
    ic = (c[0] + w * look, c[1] + hh * 0.08)
    irx, iry = w * 0.42 * isc, hh * 0.48 * isc
    iris = X(ell(ic[0], ic[1], irx, iry, n=40))
    ys = [p[1] for p in iris]
    cv.shape(iris, Grad(pal["iris_top"], pal["iris"], min(ys), max(ys) - iry * 0.25), clip=[wp])
    cv.shape(iris, None, C(pal["pupil"]), shift=iry * 0.40, clip=[wp], light=(0, 1), alpha=140)
    cv.shape(X(ell(ic[0], ic[1] + iry * 0.52, irx * 0.68, iry * 0.32, n=24)), C(pal["iris_lt"]),
             clip=[iris, wp], alpha=235)
    ring = X(ell(ic[0], ic[1] + iry * 0.06, irx * 0.74, iry * 0.76, n=36))
    cv.polyline(ring + ring[:2], C(pal["iris_lt"]), R * 0.012, alpha=120, clip=[iris, wp], caps=False)
    for k in range(7):   # radial sparkle strokes, lower half
        a = math.radians(25 + k * 21.7)
        p0 = (ic[0] + irx * 0.46 * math.cos(a), ic[1] + iry * 0.46 * math.sin(a))
        p1 = (ic[0] + irx * 0.86 * math.cos(a), ic[1] + iry * 0.86 * math.sin(a))
        cv.polyline(X([p0, p1]), C(pal["iris_lt"]), R * 0.010, alpha=95, clip=[iris, wp])
    pr = 0.62 if state == "surprised" else 1.0
    cv.shape(X(ell(ic[0], ic[1] - iry * 0.04, irx * 0.40 * pr, iry * 0.44 * pr, n=24)), C(pal["pupil"]), clip=[wp])
    cv.polyline(iris + iris[:2], C(pal["iris_ring"]), lw * 0.45, clip=[wp], caps=False)
    white = C(pal["white"])
    if state == "sparkle":
        cv.shape(X(star(ic[0] - irx * 0.22, ic[1] - iry * 0.26, irx * 0.62, 4, 0.26)), white, clip=[wp])
        cv.shape(X(star(ic[0] + irx * 0.42, ic[1] + iry * 0.42, irx * 0.30, 4, 0.30)), white, clip=[wp])
    else:
        big = 1.25 if state == "teary" else 1.0
        cv.shape(X(ell(ic[0] - irx * 0.34, ic[1] - iry * 0.40, irx * 0.36 * big, iry * 0.26 * big, n=20)),
                 white, clip=[wp])
        cv.shape(X(ell(ic[0] + irx * 0.42, ic[1] + iry * 0.40, irx * 0.15 * big, irx * 0.15 * big, n=14)),
                 white, clip=[wp])
        cv.shape(X(ell(ic[0] + irx * 0.06, ic[1] - iry * 0.66, irx * 0.07, irx * 0.07, n=10)), white, clip=[wp])
    if state == "teary":
        pool = X(ell(c[0], c[1] + hh * 0.38, w * 0.54, hh * 0.24, n=28))
        cv.shape(pool, C(pal["tear"]), clip=[wp], alpha=150)
        cv.polyline(X(qbez((c[0] - w * 0.34, c[1] + hh * 0.22), (c[0], c[1] + hh * 0.15),
                           (c[0] + w * 0.34, c[1] + hh * 0.22), 10)), white, R * 0.025, clip=[wp])

    th = R * 0.09
    if state in ("smug", "angry"):
        cut = (c[1] + hh * 0.02, c[1] - hh * 0.04) if state == "smug" else (c[1] - hh * 0.06, c[1] - hh * 0.42)
        band, edge, _ = lash_band(c, w, hh, outer, th, cut=cut)
        lid = edge + [(edge[-1][0] + outer * 0, c[1] - hh * 0.9), (edge[0][0], c[1] - hh * 0.9)]
        cv.shape(X(lid), C(pal["skin"]), clip=[wp])
        cv.shape(X(band), lash, None, lash, lw * 0.35)
    else:
        band, edge, top = lash_band(c, w, hh, outer, th)
        cv.shape(X(band), lash, None, lash, lw * 0.35)
        n = len(top)
        for u, length in ((0.84, 0.17), (0.66, 0.12)):   # lash spikes at the outer corner
            idx = int(u * (n - 1)) if outer > 0 else int((1 - u) * (n - 1))
            bx, by = top[idx]
            cv.shape(X([(bx - outer * w * 0.05, by + th * 0.35), (bx + outer * w * 0.12, by - hh * length),
                        (bx + outer * w * 0.09, by + th * 0.45)]), lash)
        i0, i1 = (int(n * 0.35), n) if outer > 0 else (0, int(n * 0.65))
        cv.polyline(X([(x, y - R * 0.06) for x, y in top[i0:i1]]), C(pal["skin_ln"]), R * 0.02, alpha=130)
    lo = bez((c[0] + outer * w * 0.06, c[1] + hh * 0.47), (c[0] + outer * w * 0.26, c[1] + hh * 0.46),
             (c[0] + outer * w * 0.40, c[1] + hh * 0.36), (c[0] + outer * w * 0.50, c[1] + hh * 0.18), n=8)
    cv.polyline(X(lo), lash, R * 0.024, alpha=210)


def draw_mouth(cv, Mh, kind, pal, g, lw):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    X = lambda pts: apl(Mh, pts)
    mx, my = hx + 0.20 * R, hy + 0.76 * R
    ln = C(pal["skin_ln"])
    mouth = C(pal["mouth"])
    if kind == "smile":
        cv.polyline(X(qbez((mx - 0.13 * R, my - 0.03 * R), (mx, my + 0.07 * R), (mx + 0.13 * R, my - 0.04 * R))),
                    ln, R * 0.034)
    elif kind == "cat":   # ω
        for sgn in (-1, 1):
            cv.polyline(X(qbez((mx, my), (mx + sgn * 0.06 * R, my + 0.07 * R), (mx + sgn * 0.12 * R, my - 0.02 * R))),
                        ln, R * 0.032)
    elif kind == "smirk":
        cv.polyline(X(qbez((mx - 0.10 * R, my + 0.01 * R), (mx + 0.02 * R, my + 0.05 * R),
                           (mx + 0.14 * R, my - 0.06 * R))), ln, R * 0.034)
    elif kind in ("frown", "pout"):
        wdt = 0.07 if kind == "pout" else 0.11
        cv.polyline(X(qbez((mx - wdt * R, my + 0.03 * R), (mx, my - 0.03 * R), (mx + wdt * R, my + 0.03 * R))),
                    ln, R * 0.034)
    elif kind == "wavy":
        cv.polyline(X([(mx - 0.13 * R + i * 0.26 * R / 16, my + 0.025 * R * math.sin(i / 16 * math.tau * 2))
                       for i in range(17)]), ln, R * 0.030)
    elif kind in ("o", "O"):
        rr = 0.06 if kind == "o" else 0.10
        mp = X(ell(mx, my + 0.01 * R, rr * 0.92 * R, rr * 1.10 * R, n=24))
        cv.shape(mp, mouth, None, ln, lw * 0.6)
        if kind == "O":
            cv.shape(X(ell(mx, my + rr * 0.75 * R, rr * 0.62 * R, rr * 0.36 * R, n=16)), C(pal["tongue"]), clip=[mp])
    elif kind == "tongue":
        cv.polyline(X(qbez((mx - 0.11 * R, my - 0.02 * R), (mx, my + 0.06 * R), (mx + 0.12 * R, my - 0.03 * R))),
                    ln, R * 0.032)
        tp = X(ell(mx + 0.05 * R, my + 0.07 * R, 0.05 * R, 0.06 * R, n=18))
        cv.shape(tp, C(pal["tongue"]), None, ln, lw * 0.5)
    else:   # open / grin / shout
        wide = {"open": 0.17, "grin": 0.20, "shout": 0.19}[kind]
        deep = {"open": 0.17, "grin": 0.16, "shout": 0.24}[kind]
        top_l, top_r = (mx - wide * R, my - 0.06 * R), (mx + wide * R, my - 0.07 * R)
        if kind == "shout":
            top_l, top_r = (mx - wide * R, my - 0.09 * R), (mx + wide * R, my - 0.11 * R)
        pts = qbez(top_l, (mx, my - (0.0 if kind != "shout" else 0.04) * R), top_r, 10)
        pts += bez(top_r, (mx + wide * 0.9 * R, my + deep * R), (mx - wide * 0.9 * R, my + deep * R), top_l, 14)
        mp = X(pts)
        cv.shape(mp, mouth, None, ln, lw * 0.7)
        cv.shape(X(ell(mx, my + deep * 0.70 * R, wide * 0.62 * R, deep * 0.38 * R, n=20)), C(pal["tongue"]), clip=[mp])
        if kind in ("grin", "shout"):
            teeth = X([(top_l[0], top_l[1] - 0.05 * R), (top_r[0], top_r[1] - 0.05 * R),
                       (top_r[0], top_r[1] + 0.045 * R), (top_l[0], top_l[1] + 0.045 * R)])
            cv.shape(teeth, C(pal["teeth"]), clip=[mp])
        if kind == "shout":   # one fang
            f0 = (mx - 0.09 * R, my - 0.075 * R)
            cv.shape(X([(f0[0] - 0.03 * R, f0[1]), (f0[0] + 0.03 * R, f0[1]), (f0[0], f0[1] + 0.07 * R)]),
                     C(pal["teeth"]), None, ln, lw * 0.35)


def draw_brows(cv, Mh, kind, pal, g):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    X = lambda pts: apl(Mh, pts)
    for which in ("near", "far"):
        c, w, h, outer = eye_params(which, hx, hy, R)
        by = c[1] - h * 0.80
        inner, outer_d = 0.0, 0.0
        if kind == "up":
            by -= 0.08 * R
        elif kind == "worried":
            inner, outer_d = -0.08 * R, 0.03 * R
        elif kind == "angry":
            inner, outer_d = 0.09 * R, -0.04 * R
        elif kind == "determined":
            inner, outer_d = 0.05 * R, -0.02 * R
        ix = c[0] - outer * w * 0.45
        ox = c[0] + outer * w * 0.45
        p_in = (ix, by + inner + (0.03 * R if outer > 0 else 0.03 * R))
        p_out = (ox, by + outer_d + 0.02 * R)
        ctrl = ((ix + ox) / 2, by - 0.09 * R + (inner + outer_d) * 0.3)
        width = R * (0.048 if kind in ("angry", "determined") else 0.040)
        cv.polyline(X(qbez(p_in, ctrl, p_out, 10)), C(pal["hair_ln"]), width, alpha=200)


def draw_extras(cv, Mh, extras, pal, g, lw, stage, phase=0.0):
    """Anime FX marks. stage 'face' = on the skin, 'top' = over the hair."""
    R, hx, hy = g["R"], g["hx"], g["hy"]
    X = lambda pts: apl(Mh, pts)
    if stage == "face":
        if "blush_lines" in extras:
            for (bx, by, sc) in ((hx - 0.46 * R, hy + 0.60 * R, 1.0), (hx + 0.54 * R, hy + 0.58 * R, 0.7)):
                for i in range(3):
                    x = bx + (i - 1) * 0.07 * R * sc
                    cv.polyline(X([(x + 0.035 * R * sc, by - 0.04 * R), (x - 0.035 * R * sc, by + 0.04 * R)]),
                                C((228, 92, 116)), R * 0.020)
        if "tears" in extras:
            for which, sc in (("near", 1.0), ("far", 0.75)):
                c, w, h, outer = eye_params(which, hx, hy, R)
                x0 = c[0] + outer * w * 0.30
                spine = catmull([(x0, c[1] + h * 0.42), (x0 + outer * 0.04 * R, c[1] + h * 0.80),
                                 (x0 + outer * 0.02 * R, c[1] + h * 1.16)], n=8)
                poly = strand(spine, lambda t: R * 0.07 * sc * (0.6 + 0.6 * t))
                cv.shape(X(poly), C(pal["tear"]), None, C(pal["tear_ln"]), lw * 0.45, alpha=235)
        return
    if "sweat" in extras:
        sx, sy = hx + 1.06 * R, hy - 0.06 * R
        drop = bez((sx, sy - 0.26 * R), (sx + 0.10 * R, sy - 0.08 * R), (sx + 0.12 * R, sy + 0.08 * R), (sx, sy + 0.10 * R))
        drop += bez((sx, sy + 0.10 * R), (sx - 0.12 * R, sy + 0.08 * R), (sx - 0.10 * R, sy - 0.08 * R), (sx, sy - 0.26 * R))
        cv.shape(X(drop), C(pal["tear"]), None, C(pal["tear_ln"]), lw * 0.6)
        cv.shape(X(ell(sx - 0.035 * R, sy + 0.01 * R, 0.025 * R, 0.045 * R, n=12)), C(pal["white"]))
    if "anger" in extras:   # the cross-popping vein
        ax, ay = hx + 0.70 * R, hy - 0.98 * R
        for qx, qy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p0 = (ax + qx * 0.05 * R, ay + qy * 0.16 * R)
            p1 = (ax + qx * 0.16 * R, ay + qy * 0.05 * R)
            cv.polyline(X(qbez(p0, (ax + qx * 0.05 * R, ay + qy * 0.05 * R), p1, 8)), C(pal["anger"]), R * 0.05)
    if "sparkles" in extras:
        for (sx, sy, sr) in ((1.18, -0.78, 0.17), (-1.18, -0.88, 0.12), (1.34, 0.08, 0.09), (-1.30, 0.20, 0.07)):
            cv.shape(X(star(hx + sx * R, hy + sy * R, sr * R, 4, 0.28)), C(pal["spark"]), None,
                     C(pal["spark_ln"]), lw * 0.5)
    if "stars" in extras:   # dizzy orbit
        ox, oy = hx - 0.02 * R, hy - 1.22 * R
        orbit = ell(ox, oy, 0.82 * R, 0.20 * R, n=40)
        cv.polyline(X(orbit + orbit[:1]), C(pal["spark_ln"]), R * 0.016, alpha=150, caps=False)
        for a in (0.4 + phase * math.tau, 2.5 + phase * math.tau, 4.4 + phase * math.tau):
            px, py = ox + 0.82 * R * math.cos(a), oy + 0.20 * R * math.sin(a)
            cv.shape(X(star(px, py, 0.11 * R, 5, 0.45)), C(pal["spark"]), None, C(pal["spark_ln"]), lw * 0.5)


EXPR = {
    "smile": dict(eyes="open", mouth="smile", brows="neutral"),
    "joy": dict(eyes="happy", mouth="open", brows="up", extras=["blush_lines", "sparkles"]),
    "focus": dict(eyes="open", mouth="o", brows="determined"),
    "smug": dict(eyes="smug", mouth="cat", brows="neutral", extras=["blush_lines"]),
    "wink": dict(eyes=("happy", "open"), mouth="tongue", brows="neutral", extras=["sparkles"]),
    "surprised": dict(eyes="surprised", mouth="O", brows="up", extras=["sweat"]),
    "fired_up": dict(eyes="sparkle", mouth="grin", brows="determined", extras=["sparkles"]),
    "shout": dict(eyes="open", mouth="shout", brows="angry"),
    "pout": dict(eyes="angry", mouth="pout", brows="angry", extras=["anger", "blush_lines"]),
    "dizzy": dict(eyes="dizzy", mouth="wavy", brows="worried", extras=["sweat", "stars"]),
    "teary": dict(eyes="teary", mouth="wavy", brows="worried", extras=["tears"]),
    "effort": dict(eyes="squeeze", mouth="shout", brows="angry", extras=["sweat"]),
    "blink": dict(eyes="blink", mouth="smile", brows="neutral"),
    "cool": dict(eyes="smug", mouth="smirk", brows="neutral"),
    "cheeky": dict(eyes="open", mouth="grin", brows="up", extras=["blush_lines"]),
}
