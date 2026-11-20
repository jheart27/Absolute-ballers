"""2D math: affine transforms (bones), curves, and shape builders."""

import math


def mm(a, b):
    return (a[0] * b[0] + a[1] * b[3], a[0] * b[1] + a[1] * b[4], a[0] * b[2] + a[1] * b[5] + a[2],
            a[3] * b[0] + a[4] * b[3], a[3] * b[1] + a[4] * b[4], a[3] * b[2] + a[4] * b[5] + a[5])


def T(x, y):
    return (1.0, 0.0, x, 0.0, 1.0, y)


def Rm(deg):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return (c, -s, 0.0, s, c, 0.0)


def about(p, deg):
    return mm(T(p[0], p[1]), mm(Rm(deg), T(-p[0], -p[1])))


def ap(m, p):
    return (m[0] * p[0] + m[1] * p[1] + m[2], m[3] * p[0] + m[4] * p[1] + m[5])


def apl(m, pts):
    return [ap(m, p) for p in pts]


def mrot(m):
    return math.degrees(math.atan2(m[3], m[0]))


def lerp(a, b, t):
    return a + (b - a) * t


def unit(v):
    L = math.hypot(v[0], v[1]) or 1e-6
    return (v[0] / L, v[1] / L)


def bez(p0, c0, c1, p1, n=18):
    out = []
    for i in range(n):
        t = i / n
        u = 1 - t
        out.append((u * u * u * p0[0] + 3 * u * u * t * c0[0] + 3 * u * t * t * c1[0] + t * t * t * p1[0],
                    u * u * u * p0[1] + 3 * u * u * t * c0[1] + 3 * u * t * t * c1[1] + t * t * t * p1[1]))
    return out


def qbez(p0, c, p1, n=12):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                    u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
    return out


def ell(cx, cy, rx, ry, a0=0.0, a1=math.tau, n=48):
    full = abs(a1 - a0) >= math.tau - 1e-6
    count = n if full else n + 1
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n),
             cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(count)]


def rell(cx, cy, rx, ry, ang, n=32):
    """Ellipse rotated by ang (radians)."""
    c, s = math.cos(ang), math.sin(ang)
    out = []
    for i in range(n):
        t = math.tau * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def fluffy(cx, cy, rx, ry, a0, a1, bumps, amp, n=72):
    """Ellipse arc whose radius swells into rounded tufts between a0..a1."""
    out = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        k = 1.0 + amp * math.sin(bumps * math.pi * i / n) ** 2
        out.append((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t)))
    return out


def star(cx, cy, r, points=4, inner=0.32, rot=-math.pi / 2):
    out = []
    for i in range(points * 2):
        rr = r if i % 2 == 0 else r * inner
        a = rot + math.pi * i / points
        out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out


def capsule(p0, w0, p1, w1, n=10):
    a = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    pts = []
    for i in range(n + 1):
        t = a - math.pi / 2 + math.pi * i / n
        pts.append((p1[0] + w1 / 2 * math.cos(t), p1[1] + w1 / 2 * math.sin(t)))
    for i in range(n + 1):
        t = a + math.pi / 2 + math.pi * i / n
        pts.append((p0[0] + w0 / 2 * math.cos(t), p0[1] + w0 / 2 * math.sin(t)))
    return pts


def catmull(points, n=8):
    out = []
    P = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                       + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(points[-1])
    return out


def _normals(spine):
    n = len(spine)
    out = []
    for i in range(n):
        q = spine[min(i + 1, n - 1)]
        r = spine[max(i - 1, 0)]
        dx, dy = q[0] - r[0], q[1] - r[1]
        L = math.hypot(dx, dy) or 1e-6
        out.append((-dy / L, dx / L))
    return out


def strand(spine, w0, w1=None):
    """Tapered ribbon along a polyline. w0/w1 = linear taper, or w0 = width(t)."""
    prof = w0 if callable(w0) else (lambda t: lerp(w0, w1, t))
    left, right = [], []
    n = len(spine)
    for i, (p, nv) in enumerate(zip(spine, _normals(spine))):
        w = prof(i / (n - 1)) / 2
        left.append((p[0] + nv[0] * w, p[1] + nv[1] * w))
        right.append((p[0] - nv[0] * w, p[1] - nv[1] * w))
    return left + right[::-1]


def offset_line(spine, d):
    return [(p[0] + nv[0] * d, p[1] + nv[1] * d) for p, nv in zip(spine, _normals(spine))]
