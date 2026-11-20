"""Hair: bangs, back hair (cap / bob / long), swinging tails, buns, side
locks, shine, strand lines, ahoge."""

import math

from .geom import apl, catmull, ell, fluffy, lerp, offset_line, qbez, strand, unit
from .paint import C, Grad


BANGS = {
    "default": [(0.88, 0.12, "t"), (0.70, -0.24, "n"), (0.56, 0.10, "t"), (0.38, -0.28, "n"),
                (0.22, 0.16, "t"), (0.04, -0.38, "n"), (-0.14, 0.18, "t"), (-0.32, -0.26, "n"),
                (-0.50, 0.14, "t"), (-0.68, -0.18, "n"), (-0.88, 0.20, "t")],
    "blunt": [(0.88, 0.12, "t"), (0.72, -0.04, "n"), (0.56, 0.14, "t"), (0.40, -0.02, "n"),
              (0.24, 0.15, "t"), (0.08, -0.04, "n"), (-0.10, 0.16, "t"), (-0.28, -0.02, "n"),
              (-0.46, 0.15, "t"), (-0.66, -0.02, "n"), (-0.88, 0.16, "t")],
    "swept": [(0.88, 0.06, "t"), (0.66, -0.32, "n"), (0.50, 0.04, "t"), (0.30, -0.34, "n"),
              (0.10, 0.14, "t"), (-0.04, -0.28, "n"), (-0.22, 0.24, "t"), (-0.40, -0.16, "n"),
              (-0.58, 0.22, "t"), (-0.74, -0.08, "n"), (-0.90, 0.30, "t")],
    "spiky": [(0.88, 0.06, "t"), (0.72, -0.28, "n"), (0.58, 0.06, "t"), (0.42, -0.32, "n"),
              (0.26, 0.10, "t"), (0.08, -0.38, "n"), (-0.10, 0.12, "t"), (-0.28, -0.32, "n"),
              (-0.46, 0.08, "t"), (-0.64, -0.24, "n"), (-0.86, 0.14, "t")],
}


def bangs_poly(hx, hy, R, kind):
    c0 = (hx - 0.02 * R, hy - 0.16 * R)
    arc = ell(c0[0], c0[1], 1.05 * R, 1.02 * R, math.radians(176), math.radians(364), n=40)
    pts = list(arc)
    prev = arc[-1]
    for ox, oy, k in BANGS[kind]:
        p = (hx + ox * R, hy + oy * R)
        sweep = 1.0 if ox > 0.04 else -1.0  # locks sweep away from the parting
        if k == "t":
            ctrl = (lerp(prev[0], p[0], 0.25) + sweep * 0.05 * R, lerp(prev[1], p[1], 0.75))
        else:
            ctrl = (lerp(prev[0], p[0], 0.70) - sweep * 0.03 * R, lerp(prev[1], p[1], 0.35))
        pts += qbez(prev, ctrl, p, n=7)[1:]
        prev = p
    pts += qbez(prev, (lerp(prev[0], arc[0][0], 0.5) - 0.04 * R, lerp(prev[1], arc[0][1], 0.6)),
                arc[0], n=7)[1:]
    return pts


def cap_poly(hx, hy, R):
    c = (hx - 0.06 * R, hy - 0.12 * R)
    a0, a1 = math.radians(112), math.radians(300)
    back = fluffy(c[0], c[1], 1.08 * R, 1.06 * R, a0, a1, 5, 0.05, n=60)
    rest = ell(c[0], c[1], 1.08 * R, 1.06 * R, a1, a0 + math.tau, n=48)
    return back + rest[1:]


def bob_poly(hx, hy, R):
    c = (hx - 0.04 * R, hy - 0.14 * R)
    top = fluffy(c[0], c[1], 1.13 * R, 1.09 * R, math.radians(158), math.radians(382), 4, 0.03, n=60)
    right = catmull([top[-1], (hx + 1.07 * R, hy + 0.42 * R), (hx + 1.00 * R, hy + 0.86 * R),
                     (hx + 0.80 * R, hy + 1.00 * R)], n=6)
    bottom = [(hx + 0.40 * R, hy + 0.98 * R), (hx - 0.30 * R, hy + 1.02 * R), (hx - 0.86 * R, hy + 1.04 * R)]
    left = catmull([(hx - 1.08 * R, hy + 0.94 * R), (hx - 1.17 * R, hy + 0.50 * R), top[0]], n=6)
    return top + right + bottom + left


SIDE_LOCKS = {
    "short": ([(-0.90, -0.30), (-0.99, 0.20), (-0.94, 0.58), (-0.82, 0.94)], 0.26, 0.03,
              [(0.87, -0.26), (0.96, 0.16), (0.89, 0.54)], 0.20, 0.03),
    "bob": ([(-0.92, -0.30), (-1.03, 0.30), (-0.99, 0.72), (-0.86, 1.00)], 0.34, 0.12,
            [(0.88, -0.26), (0.99, 0.26), (0.95, 0.66), (0.85, 0.92)], 0.28, 0.10),
    "long": ([(-0.90, -0.30), (-1.00, 0.30), (-0.97, 0.90), (-0.88, 1.48), (-0.74, 1.94)], 0.28, 0.03,
             [(0.87, -0.26), (0.97, 0.26), (0.92, 0.80), (0.84, 1.28)], 0.22, 0.03),
    "buns": ([(-0.90, -0.30), (-0.97, 0.12), (-0.88, 0.52)], 0.22, 0.03,
             [(0.87, -0.26), (0.94, 0.10), (0.88, 0.44)], 0.18, 0.03),
}


TAILS = {
    "ponytail": [dict(root=(-0.80, -0.48), segs=[(-0.30, 0.50), (-0.12, 0.52), (0.06, 0.46)], prof="pony")],
    "twintails": [dict(root=(-0.84, -0.40), segs=[(-0.22, 0.52), (-0.10, 0.56), (0.08, 0.52)], prof="twin"),
                  dict(root=(0.80, -0.50), segs=[(0.26, 0.54), (0.10, 0.58), (-0.06, 0.52)], prof="twin")],
}


def tail_prof(kind, R):
    if kind == "pony":
        return lambda t: R * ((0.30 + 0.36 * math.sin(t / 0.30 * math.pi / 2)) if t < 0.30
                              else (0.66 * (1 - (t - 0.30) / 0.70) ** 0.85 + 0.02))
    return lambda t: R * ((0.22 + 0.32 * math.sin(t / 0.25 * math.pi / 2)) if t < 0.25
                          else (0.54 * (1 - (t - 0.25) / 0.75) ** 0.75 + 0.02))


def tail_points(Mh, g, spec, ang):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    p = (hx + spec["root"][0] * R, hy + spec["root"][1] * R)
    pts = [p]
    acc = 0.0
    for (dx, dy), a in zip(spec["segs"], ang):
        acc += a
        c, s = math.cos(math.radians(acc)), math.sin(math.radians(acc))
        vx, vy = dx * R, dy * R
        p = (p[0] + vx * c - vy * s, p[1] + vx * s + vy * c)
        pts.append(p)
    return apl(Mh, pts)


def hair_shape(cv, poly, pal, lw, R, shift=0.15):
    ys = [p[1] for p in poly]
    cv.shape(poly, Grad(pal["hair_top"], pal["hair_bot"], min(ys), max(ys)), C(pal["hair_sh"]),
             C(pal["hair_ln"]), lw, shift=R * shift)


def draw_tails(cv, Mh, g, pal, P, style, ang):
    R, lw = g["R"], P["lw"]
    roots = []
    for spec in TAILS.get(style, []):
        pts = tail_points(Mh, g, spec, ang)
        spine = catmull(pts, n=10)
        poly = strand(spine, tail_prof(spec["prof"], R))
        hair_shape(cv, poly, pal, lw, R)
        for off in (-0.12, 0.10):
            cv.polyline(offset_line(spine[3:-5], off * R), C(pal["hair_sh"]), R * 0.022, clip=[poly])
        cv.polyline(offset_line(spine[2:len(spine) // 2], -0.07 * R), C(pal["hair_hi"]), R * 0.04,
                    alpha=210, clip=[poly])
        roots.append(pts[0])
    return roots


def draw_long_back(cv, Mh, g, pal, P, ang):
    R, hx, hy = g["R"], g["hx"], g["hy"]
    src = [(-0.66, -0.86), (-1.10, -0.20), (-1.22, 0.60), (-1.18, 1.40), (-1.04, 2.02), (-0.70, 2.16),
           (-0.36, 2.02), (-0.08, 2.12), (0.20, 1.86), (0.42, 1.30), (0.78, 0.70), (1.02, 0.02), (0.80, -0.74)]
    pivot = (hx - 0.10 * R, hy - 0.40 * R)
    pts = []
    for x, y in src:
        px, py = hx + x * R, hy + y * R
        k = max(0.0, (y + 0.2) / 2.3)
        a = math.radians(ang[0] * 0.35 * k + ang[1] * 0.2 * k * k)
        dx, dy = px - pivot[0], py - pivot[1]
        pts.append((pivot[0] + dx * math.cos(a) - dy * math.sin(a), pivot[1] + dx * math.sin(a) + dy * math.cos(a)))
    poly = apl(Mh, catmull(pts + [pts[0]], n=6))
    hair_shape(cv, poly, pal, P["lw"], R)
    for i, xs in enumerate((-0.90, -0.55, -0.20, 0.30)):
        line = apl(Mh, catmull([(hx + xs * R, hy + 0.2 * R), (hx + (xs - 0.05) * R, hy + 1.0 * R),
                                (hx + (xs - 0.02) * R, hy + 1.8 * R)], n=6))
        cv.polyline(line, C(pal["hair_sh"]), R * 0.022, clip=[poly])


def draw_buns(cv, Mh, g, pal, P):
    R, hx, hy, lw = g["R"], g["hx"], g["hy"], P["lw"]
    for bx, by, br in ((0.46, -1.04, 0.25), (-0.60, -0.94, 0.30)):   # far bun first
        cx, cy = hx + bx * R, hy + by * R
        poly = apl(Mh, fluffy(cx, cy, br * R, br * R, 0, math.tau, 6, 0.05, n=60)[:-1])
        hair_shape(cv, poly, pal, lw, R, shift=0.08)
        swirl = [(cx + br * R * 0.55 * (1 - t / 7) * math.cos(t + 2.4), cy + br * R * 0.55 * (1 - t / 7) * math.sin(t + 2.4))
                 for t in [i * 0.2 for i in range(20)]]
        cv.polyline(apl(Mh, swirl), C(pal["hair_sh"]), R * 0.024, clip=[poly])


def angel_ring(hx, hy, R):
    """Glossy highlight band with a zigzag lower edge (shine across strands)."""
    c0 = (hx - 0.02 * R, hy - 0.16 * R)
    a0, a1 = math.radians(206), math.radians(330)
    outer = ell(c0[0], c0[1], 0.90 * R, 0.86 * R, a0, a1, n=24)
    inner = []
    teeth = 9
    for i in range(teeth * 2 + 1):
        t = a1 + (a0 - a1) * i / (teeth * 2)
        r = 0.80 if i % 2 == 0 else (0.70, 0.74, 0.67, 0.72, 0.69, 0.75, 0.68, 0.73, 0.70)[(i // 2) % 9]
        inner.append((c0[0] + r * R * 0.98 * math.cos(t), c0[1] + r * R * 0.94 * math.sin(t)))
    return outer + inner


def draw_front_hair(cv, Mh, g, pal, P, ch):
    R, hx, hy, lw = g["R"], g["hx"], g["hy"], P["lw"]
    X = lambda pts: apl(Mh, pts)
    style = ch["style"]
    key = {"ponytail": "short", "twintails": "short", "bob": "bob", "long": "long", "buns": "buns",
           "short": "buns"}[style]
    nl, nw0, nw1, fl, fw0, fw1 = SIDE_LOCKS[key]
    for pts, w0, w1 in ((fl, fw0, fw1), (nl, nw0, nw1)):
        spine = catmull([(hx + x * R, hy + y * R) for x, y in pts], n=8)
        poly = X(strand(spine, w0 * R, w1 * R))
        hair_shape(cv, poly, pal, lw, R, shift=0.08)
        cv.polyline(X(offset_line(spine[2:-3], 0.02 * R)), C(pal["hair_sh"]), R * 0.02, clip=[poly])
    bp = X(bangs_poly(hx, hy, R, ch["bangs"]))
    hair_shape(cv, bp, pal, lw, R, shift=0.14)
    # lock-separation lines: rise from each notch toward the crown, tapering
    crown = (hx - 0.02 * R, hy - 1.10 * R)   # aim UP toward the crown, never sideways
    for ox, oy, k in BANGS[ch["bangs"]]:
        p = (hx + ox * R, hy + oy * R)
        if k == "n":
            d = unit((crown[0] - p[0], crown[1] - p[1]))
            ln = 0.26 * R + 0.10 * R * (1 - abs(ox))
            spine = catmull([p, (p[0] + d[0] * ln * 0.5 + 0.03 * R * (1 if ox > 0 else -1), p[1] + d[1] * ln * 0.5),
                             (p[0] + d[0] * ln, p[1] + d[1] * ln)], n=8)
            cv.shape(X(strand(spine, lambda t: R * (0.032 * (1 - t) + 0.004))), C(pal["hair_sh"]),
                     clip=[bp], alpha=235)
        else:   # faint flow line up the middle of each lock
            spine = catmull([(p[0], p[1] - 0.05 * R), (p[0] - 0.02 * R * (1 if ox > 0 else -1), p[1] - 0.18 * R),
                             (p[0], p[1] - 0.30 * R)], n=6)
            cv.shape(X(strand(spine, lambda t: R * (0.020 * (1 - t) + 0.003))), C(pal["hair_sh"]),
                     clip=[bp], alpha=120)
    cv.shape(X(angel_ring(hx, hy, R)), C(pal["hair_hi"]), clip=[bp], alpha=215)
    if ch.get("ahoge"):   # the rebellious antenna lock, with a curl
        ah = strand(catmull([(hx + 0.02 * R, hy - 1.04 * R), (hx + 0.05 * R, hy - 1.34 * R),
                             (hx + 0.22 * R, hy - 1.56 * R), (hx + 0.44 * R, hy - 1.54 * R),
                             (hx + 0.48 * R, hy - 1.38 * R), (hx + 0.36 * R, hy - 1.32 * R)], n=8),
                    lambda t: R * (0.10 * (1 - t) ** 0.8 + 0.012))
        hair_shape(cv, X(ah), pal, lw * 0.85, R, shift=0.03)
    return bp
