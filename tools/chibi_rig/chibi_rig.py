#!/usr/bin/env python3
"""Chibi rig renderer — the Absolute Ballers character art pipeline.

A 2D cutout rig (the Spine / gacha battle-sprite approach) authored and posed
entirely in code:

  * a bone hierarchy with forward kinematics (body, legs),
  * stretchy 2-bone IK for the arms (hands land on the ball),
  * swinging hair chains (ponytail, twintails, long hair),
  * a layered face with an expression library (eyes x mouth x brows x FX),
  * cel shading with gradient fills, colored lineart, and a sticker-style
    outer stroke around the whole character.

Characters are data (palette + hairstyle + kit + eye shape) and poses are data
(bone angles + IK targets), so the whole cast shares one rig, one pose set and
one expression set. Everything renders at 4x and is downsampled for clean
anime lineart.

Usage:
  python3 tools/chibi_rig/chibi_rig.py showcase docs/art   # all sheets + GIF
  python3 tools/chibi_rig/chibi_rig.py one aki dribble joy out.png
"""
import colorsys
import math
import os
import sys
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SS = 4                      # supersampling factor
LIGHT = (-0.55, -0.83)      # light from the upper-left
OUTLINE = (42, 24, 52)      # sticker stroke around the whole character


# =================================================================== affine
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


# ================================================================= geometry
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


# ==================================================================== color
def C(c, a=255):
    return (int(c[0]), int(c[1]), int(c[2]), a)


def hsv(c, ds=1.0, dv=1.0, dh=0.0):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255.0 for x in c[:3]))
    r, g, b = colorsys.hsv_to_rgb((h + dh) % 1.0, max(0.0, min(1.0, s * ds)),
                                  max(0.0, min(1.0, v * dv)))
    return (int(r * 255), int(g * 255), int(b * 255))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dim(c, k=0.86):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k), c[3] if len(c) > 3 else 255)


class Grad:
    """Vertical gradient fill in world coordinates (top color -> bottom color)."""

    def __init__(self, c0, c1, y0, y1):
        self.c0, self.c1, self.y0, self.y1 = C(c0), C(c1), y0, y1


# =================================================================== canvas
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _box(self, pts, pad):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0 = max(0, int(min(xs) * SS - pad))
        y0 = max(0, int(min(ys) * SS - pad))
        x1 = min(self.img.width, int(max(xs) * SS + pad) + 1)
        y1 = min(self.img.height, int(max(ys) * SS + pad) + 1)
        return (x0, y0, x1, y1)

    def _mask(self, pts, box, dx=0.0, dy=0.0):
        x0, y0, x1, y1 = box
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(m).polygon(
            [((x + dx) * SS - x0, (y + dy) * SS - y0) for x, y in pts], fill=255)
        return m

    def _fill(self, fill, box):
        size = (box[2] - box[0], box[3] - box[1])
        if isinstance(fill, Grad):
            span = (fill.y1 - fill.y0) * SS or 1.0
            col = Image.new("L", (1, size[1]))
            col.putdata([int(max(0.0, min(1.0, (box[1] + j - fill.y0 * SS) / span)) * 255)
                         for j in range(size[1])])
            return Image.composite(Image.new("RGBA", size, fill.c1),
                                   Image.new("RGBA", size, fill.c0),
                                   col.resize(size, Image.NEAREST))
        return Image.new("RGBA", size, fill)

    def shape(self, pts, fill=None, shadow=None, line=None, lw=2.4, shift=5.0,
              clip=None, light=LIGHT, alpha=255):
        box = self._box(pts, (lw + shift + 4) * SS)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        m = self._mask(pts, box)
        for c in clip or []:
            m = ImageChops.multiply(m, self._mask(c, box))
        if alpha < 255:
            m = m.point(lambda v: v * alpha // 255)
        size = (box[2] - box[0], box[3] - box[1])
        if fill is not None:
            self.img.paste(self._fill(fill, box), box[:2], m)
        if shadow is not None:
            sh = self._mask(pts, box, light[0] * shift, light[1] * shift)
            self.img.paste(Image.new("RGBA", size, shadow), box[:2], ImageChops.subtract(m, sh))
        if line is not None:
            P = [(x * SS, y * SS) for x, y in pts]
            self.d.line(P + P[:2], fill=line, width=max(1, int(lw * SS)), joint="curve")

    def union(self, polys, fill, shadow=None, line=None, lw=2.4, shift=5.0, light=LIGHT):
        """One silhouette from overlapping polygons: one fill, one cel shadow,
        ONE outline around the union — no seams where segments overlap (this
        is what skinned-mesh limbs look like in a rig)."""
        allpts = [p for poly in polys for p in poly]
        box = self._box(allpts, (lw + shift + 6) * SS)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        size = (box[2] - box[0], box[3] - box[1])
        m = Image.new("L", size, 0)
        for poly in polys:
            m = ImageChops.lighter(m, self._mask(poly, box))
        self.img.paste(self._fill(fill, box), box[:2], m)
        if shadow is not None:
            ms = Image.new("L", size, 0)
            for poly in polys:
                ms = ImageChops.lighter(ms, self._mask(poly, box, light[0] * shift, light[1] * shift))
            self.img.paste(Image.new("RGBA", size, shadow), box[:2], ImageChops.subtract(m, ms))
        if line is not None:
            k = max(3, int(lw * SS) | 1)
            edge = ImageChops.subtract(m.filter(ImageFilter.MaxFilter(k)),
                                       m.filter(ImageFilter.MinFilter(k)))
            self.img.paste(Image.new("RGBA", size, line), box[:2], edge)

    def polyline(self, pts, color, lw, alpha=255, clip=None, caps=True):
        box = self._box(pts, (lw + 4) * SS)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        x0, y0 = box[:2]
        size = (box[2] - box[0], box[3] - box[1])
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        P = [(x * SS - x0, y * SS - y0) for x, y in pts]
        w = max(1, int(lw * SS))
        solid = color[:3] + (255,)
        d.line(P, fill=solid, width=w, joint="curve")
        if caps:
            r = w / 2
            for (x, y) in (P[0], P[-1]):
                d.ellipse([x - r, y - r, x + r, y + r], fill=solid)
        a = layer.getchannel("A")
        if alpha < 255:
            a = a.point(lambda v: v * alpha // 255)
        for c in clip or []:
            a = ImageChops.multiply(a, self._mask(c, box))
        layer.putalpha(a)
        self.img.alpha_composite(layer, dest=(x0, y0))

    def blob(self, pts, color, radius):
        box = self._box(pts, radius * 3 * SS)
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        x0, y0 = box[:2]
        size = (box[2] - box[0], box[3] - box[1])
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon([(x * SS - x0, y * SS - y0) for x, y in pts], fill=color)
        layer = layer.filter(ImageFilter.GaussianBlur(radius * SS))
        self.img.alpha_composite(layer, dest=(x0, y0))

    def text(self, s, center, size, angle, fill, stroke, stroke_w, sx=1.0, clip=None):
        f = font(max(8, int(size * SS)))
        sw = max(1, int(stroke_w * SS))
        bb = f.getbbox(s, stroke_width=sw)
        tw, th = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
        im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((2 - bb[0], 2 - bb[1]), s, font=f, fill=fill,
                                stroke_width=sw, stroke_fill=stroke)
        if sx != 1.0:
            im = im.resize((max(1, int(tw * sx)), th), Image.LANCZOS)
        im = im.rotate(-angle, resample=Image.BICUBIC, expand=True)
        x = int(center[0] * SS - im.width / 2)
        y = int(center[1] * SS - im.height / 2)
        if clip:
            box = (x, y, x + im.width, y + im.height)
            a = im.getchannel("A")
            for c in clip:
                m = Image.new("L", im.size, 0)
                ImageDraw.Draw(m).polygon([(px * SS - x, py * SS - y) for px, py in c], fill=255)
                a = ImageChops.multiply(a, m)
            im.putalpha(a)
            del box
        if x >= 0 and y >= 0:
            self.img.alpha_composite(im, dest=(x, y))

    def outline_pass(self, color, width):
        """Sticker stroke: dilate the whole character's silhouette and put a
        solid band of `color` behind it."""
        a = self.img.getchannel("A")
        r = width * SS
        grown = a.filter(ImageFilter.GaussianBlur(r * 0.55)).point(lambda v: 255 if v > 9 else 0)
        base = Image.new("RGBA", self.img.size, C(color))
        base.putalpha(grown)
        base.alpha_composite(self.img)
        self.img = base
        self.d = ImageDraw.Draw(self.img)

    def finish(self):
        return self.img.resize((self.w, self.h), Image.LANCZOS)


@lru_cache(maxsize=None)
def font(size):
    for p in ("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
              "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# =================================================================== the cast
SKINS = {
    "fair": dict(skin=(255, 231, 216), skin_top=(255, 241, 232), skin_sh=(245, 188, 178),
                 skin_sh2=(226, 150, 150), skin_ln=(150, 84, 92), blush=(255, 124, 146)),
    "tan": dict(skin=(242, 200, 164), skin_top=(249, 216, 186), skin_sh=(216, 154, 126),
                skin_sh2=(190, 122, 104), skin_ln=(122, 68, 56), blush=(242, 110, 112)),
}

COMMON = dict(
    white=(255, 255, 255), eye_sh=(210, 212, 242), lash=(44, 18, 34),
    mouth=(152, 38, 62), tongue=(248, 130, 146), teeth=(255, 255, 255),
    sock=(250, 250, 253), sock_sh=(206, 212, 230), sock_ln=(102, 108, 140),
    shoe=(250, 250, 253), shoe_sh=(200, 208, 228), sole=(66, 62, 88),
    ball=(244, 128, 46), ball_top=(252, 162, 86), ball_sh=(192, 78, 26), ball_ln=(98, 36, 12),
    tear=(178, 220, 255), tear_ln=(92, 146, 214), spark=(255, 240, 140), spark_ln=(232, 168, 40),
    anger=(234, 52, 76), gold=(255, 212, 92), gold_sh=(214, 150, 48), gold_ln=(118, 72, 20),
)


def hair_pal(base, hi=None):
    return dict(
        hair=base,
        hair_top=mix(base, (255, 255, 255), 0.07),
        hair_bot=hsv(base, 1.10, 0.84),
        hair_sh=mix(hsv(base, 1.15, 0.66), (72, 40, 124), 0.20),   # cooler shadow
        hair_hi=hi or mix(base, (255, 255, 255), 0.68),
        hair_ln=mix(hsv(base, 1.2, 0.36), (30, 14, 40), 0.35),
    )


def eye_pal(base):
    return dict(iris=base, iris_top=hsv(base, 1.15, 0.40), iris_lt=mix(base, (255, 255, 255), 0.55),
                pupil=hsv(base, 1.25, 0.18), iris_ring=hsv(base, 1.2, 0.28))


def kit_pal(base, trim=(255, 255, 255)):
    dark = sum(base) < 200
    if dark:
        return dict(jersey=base, jersey_top=mix(base, (255, 255, 255), 0.12),
                    jersey_sh=mix(base, (0, 0, 0), 0.45), jersey_ln=(16, 10, 22),
                    trim=trim, trim_sh=mix(trim, (60, 40, 30), 0.30),
                    shorts=mix(base, (0, 0, 0), 0.12), shorts_sh=mix(base, (0, 0, 0), 0.50))
    return dict(jersey=base, jersey_top=mix(base, (255, 255, 255), 0.18),
                jersey_sh=hsv(base, 1.10, 0.74), jersey_ln=mix(hsv(base, 1.2, 0.34), (20, 12, 30), 0.4),
                trim=trim, trim_sh=mix(trim, (70, 70, 110), 0.22),
                shorts=hsv(base, 1.04, 0.88), shorts_sh=hsv(base, 1.12, 0.66))


CAST = {
    "aki": dict(name="AKI", tag="Captain of chaos", hair=(232, 62, 78), eyes=(220, 54, 76),
                kit=(64, 198, 236), skin="fair", style="ponytail", acc="scrunchie",
                bangs="default", tilt=0.15, number="7", ahoge=True, idle="wave", signature="smile"),
    "yumi": dict(name="YUMI", tag="Splash queen", hair=(88, 130, 242), eyes=(64, 116, 232),
                 kit=(255, 120, 170), skin="fair", style="twintails", acc="ribbons",
                 bangs="default", tilt=-0.45, number="3", ahoge=True, idle="peace", signature="wink"),
    "rin": dict(name="RIN", tag="Blink and she's gone", hair=(62, 56, 90), hair_hi=(160, 168, 224),
                eyes=(168, 102, 234), kit=(46, 44, 60), trim=(255, 208, 90), skin="fair",
                style="bob", acc="clip", bangs="blunt", tilt=0.75, number="11", ahoge=False,
                idle="hip", signature="smug"),
    "hana": dict(name="HANA", tag="Small package, big slam", hair=(250, 154, 194),
                 eyes=(62, 182, 134), kit=(98, 214, 172), skin="fair", style="long",
                 acc="flower", bangs="swept", tilt=-0.2, number="23", ahoge=False,
                 idle="cheer", signature="joy"),
    "miko": dict(name="MIKO", tag="Hands of a fox", hair=(250, 210, 100), eyes=(232, 128, 40),
                 kit=(68, 102, 216), skin="tan", style="buns", acc="headband", bangs="spiky",
                 tilt=0.35, number="5", ahoge=True, idle="fist", signature="fired_up"),
}


def palette(cid):
    ch = CAST[cid]
    pal = dict(COMMON)
    pal.update(SKINS[ch["skin"]])
    pal.update(hair_pal(ch["hair"], ch.get("hair_hi")))
    pal.update(eye_pal(ch["eyes"]))
    pal.update(kit_pal(ch["kit"], ch.get("trim", (255, 255, 255))))
    return pal


# ===================================================================== rig
BODY = dict(cx=180, floor=432, foot_h=10, shin=34, thigh=32, torso_low=26, torso_up=32,
            neck=5, head_r=60, shoulder_w=46, chest_w=44, waist_w=36, hip_w=46,
            upper_arm=27, fore_arm=24, hand_r=7.6, ball_r=15,
            w_up=(16, 13.5), w_lo=(13.5, 12), w_th=(24, 18), w_sh=(19, 12.5), lw=2.4, stroke=1.8)


def body_params(s=1.0, cx=None, floor=None):
    b = {k: (tuple(x * s for x in v) if isinstance(v, tuple) else v * s) for k, v in BODY.items()}
    if cx is not None:
        b["cx"] = cx
    if floor is not None:
        b["floor"] = floor
    return b


def build(P):
    cx, floor = P["cx"], P["floor"]
    ankle_y = floor - P["foot_h"]
    knee_y = ankle_y - P["shin"]
    hip_y = knee_y - P["thigh"]
    waist_y = hip_y - P["torso_low"]
    sh_y = waist_y - P["torso_up"]
    chin_y = sh_y - P["neck"]
    R = P["head_r"]
    hx, hy = cx + R * 0.10, chin_y - R * 0.98
    sw, hw = P["shoulder_w"], P["hip_w"]
    J = {
        "pelvis": (cx, hip_y), "waist": (cx, waist_y), "neck": (cx + 2 * R / 60, sh_y + 2),
        "chin": (hx + R * 0.10, chin_y),
        "sh_n": (cx - sw * 0.46, sh_y + 4 * R / 60), "sh_f": (cx + sw * 0.40, sh_y + 3 * R / 60),
        "hp_n": (cx - hw * 0.22, hip_y + 2 * R / 60), "hp_f": (cx + hw * 0.24, hip_y),
    }
    for s in ("n", "f"):
        sx, sy = J["sh_" + s]
        J["el_" + s] = (sx, sy + P["upper_arm"])
        J["wr_" + s] = (sx, sy + P["upper_arm"] + P["fore_arm"])
        hpx, _ = J["hp_" + s]
        J["kn_" + s] = (hpx, knee_y)
        J["an_" + s] = (hpx, ankle_y)
    bones = [
        ("root", None, J["pelvis"]), ("chest", "root", J["waist"]),
        ("neck", "chest", J["neck"]), ("head", "neck", J["chin"]),
        ("f_up", "chest", J["sh_f"]), ("f_lo", "f_up", J["el_f"]),
        ("n_up", "chest", J["sh_n"]), ("n_lo", "n_up", J["el_n"]),
        ("f_th", "root", J["hp_f"]), ("f_sh", "f_th", J["kn_f"]), ("f_ft", "f_sh", J["an_f"]),
        ("n_th", "root", J["hp_n"]), ("n_sh", "n_th", J["kn_n"]), ("n_ft", "n_sh", J["an_n"]),
    ]
    g = dict(hx=hx, hy=hy, R=R, cx=cx, floor=floor, hip_y=hip_y, waist_y=waist_y,
             sh_y=sh_y, chin_y=chin_y, knee_y=knee_y, ankle_y=ankle_y)
    return J, bones, g


def solve(bones, pose):
    M = {}
    tx, ty = pose.get("_t", (0.0, 0.0))
    for name, parent, piv in bones:
        base = M[parent] if parent else T(tx, ty)
        M[name] = mm(base, about(piv, pose.get(name, 0.0)))
    return M


def ik2(S, target, L1, L2, bend, max_stretch=1.0):
    """Stretchy 2-bone IK (like Spine's IK constraint with stretch). Returns
    elbow and wrist world positions."""
    dx, dy = target[0] - S[0], target[1] - S[1]
    dist = math.hypot(dx, dy)
    s = 1.0
    if dist > (L1 + L2) * 0.98:
        s = min(max_stretch, dist / ((L1 + L2) * 0.98))
    L1, L2 = L1 * s, L2 * s
    d = max(abs(L1 - L2) + 0.01, min(L1 + L2 - 0.01, dist))
    base = math.atan2(dy, dx)
    a1 = math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    phi1 = base + bend * a1
    E = (S[0] + L1 * math.cos(phi1), S[1] + L1 * math.sin(phi1))
    W = (S[0] + d * math.cos(base), S[1] + d * math.sin(base))
    return E, W


def arm_joints(M, J, P, pose, side):
    S = ap(M["chest"], J["sh_" + side])
    spec = pose.get("ik_" + side)
    if spec:
        target, bend, stretch = spec
        E, W = ik2(S, target, P["upper_arm"], P["fore_arm"], bend, stretch)
        return S, E, W
    return S, ap(M[side + "_up"], J["el_" + side]), ap(M[side + "_lo"], J["wr_" + side])


# ============================================================ body drawing
def draw_arm(cv, joints, P, pal, far, band, hand="mitten"):
    S, E, W = joints
    k = 0.88 if far else 1.0
    sk, sks, ln = dim(C(pal["skin"]), k), dim(C(pal["skin_sh"]), k), C(pal["skin_ln"])
    d = unit((W[0] - E[0], W[1] - E[1]))
    hr = P["hand_r"]
    ang = math.atan2(d[1], d[0]) - math.pi / 2
    fwd = (d[1], -d[0]) if d[1] >= 0 else (-d[1], d[0])
    if fwd[0] < 0:
        fwd = (-fwd[0], -fwd[1])
    hc = (W[0] + d[0] * hr * 0.80, W[1] + d[1] * hr * 0.80)
    thumb = rell(W[0] + d[0] * hr * 0.36 + fwd[0] * hr * 0.70, W[1] + d[1] * hr * 0.36 + fwd[1] * hr * 0.70,
                 hr * 0.42, hr * 0.50, ang, 16)
    polys = [capsule(S, P["w_up"][0], E, P["w_up"][1]), capsule(E, P["w_lo"][0], W, P["w_lo"][1])]
    if hand == "peace":   # V sign: palm + two raised fingers
        polys += [rell(hc[0], hc[1], hr * 0.92, hr * 0.98, ang, 24), thumb]
        base = (hc[0] + d[0] * hr * 0.50, hc[1] + d[1] * hr * 0.50)
        for sgn in (-1, 1):
            a = math.atan2(d[1], d[0]) + sgn * 0.26
            polys.append(capsule(base, hr * 0.50, (base[0] + math.cos(a) * hr * 1.50,
                                                   base[1] + math.sin(a) * hr * 1.50), hr * 0.42))
    elif hand == "fist":
        polys += [rell(hc[0], hc[1], hr * 1.04, hr * 1.04, ang, 24)]
    else:
        polys += [rell(hc[0], hc[1], hr * 0.98, hr * 1.16, ang, 28), thumb]
    cv.union(polys, sk, sks, ln, P["lw"], shift=P["w_up"][0] * 0.34)
    if hand == "fist":   # knuckle creases
        for i in (-1, 1):
            o = (hc[0] + d[0] * hr * 0.30 + fwd[0] * hr * 0.35 * i, hc[1] + d[1] * hr * 0.30 + fwd[1] * hr * 0.35 * i)
            cv.polyline([o, (o[0] + d[0] * hr * 0.45, o[1] + d[1] * hr * 0.45)], ln, P["lw"] * 0.45)
    if band:  # wristband in the kit color
        w = P["w_lo"][1] + 2.8 * P["head_r"] / 60
        nv = (-d[1], d[0])
        a = (W[0] - d[0] * P["fore_arm"] * 0.36, W[1] - d[1] * P["fore_arm"] * 0.36)
        b = (W[0] - d[0] * P["fore_arm"] * 0.06, W[1] - d[1] * P["fore_arm"] * 0.06)
        quad = [(a[0] + nv[0] * w / 2, a[1] + nv[1] * w / 2), (b[0] + nv[0] * w / 2, b[1] + nv[1] * w / 2),
                (b[0] - nv[0] * w / 2, b[1] - nv[1] * w / 2), (a[0] - nv[0] * w / 2, a[1] - nv[1] * w / 2)]
        cv.shape(quad, C(pal["jersey"]), C(pal["jersey_sh"]), C(pal["jersey_ln"]), P["lw"] * 0.85, shift=2.0)


def draw_leg(cv, M, J, P, pal, side, far):
    k = 0.88 if far else 1.0
    sk, sks, ln = dim(C(pal["skin"]), k), dim(C(pal["skin_sh"]), k), C(pal["skin_ln"])
    lw, R = P["lw"], P["head_r"]
    H, K, A = J["hp_" + side], J["kn_" + side], J["an_" + side]
    th, shn, ft = M[side + "_th"], M[side + "_sh"], M[side + "_ft"]
    ws = P["w_sh"][0]
    polys = [
        apl(th, capsule(H, P["w_th"][0], K, P["w_th"][1])),
        apl(shn, capsule(K, ws, A, P["w_sh"][1])),
        apl(shn, ell(K[0] - ws * 0.16, K[1] + P["shin"] * 0.34, ws * 0.58, P["shin"] * 0.28, n=24)),
    ]
    cv.union(polys, sk, sks, ln, lw, shift=P["w_th"][0] * 0.30)
    # occlusion shadow where the shorts hem meets the thigh
    w2 = P["w_th"][0] + 5.5 * R / 60
    hem = H[1] + P["thigh"] * 0.42
    cv.shape(apl(th, [(H[0] - w2 / 2, hem - 2), (H[0] + w2 / 2, hem - 2),
                      (H[0] + w2 / 2, hem + 3.5 * R / 60), (H[0] - w2 / 2, hem + 3.5 * R / 60)]),
             dim(C(pal["skin_sh"]), k), clip=[polys[0]])
    # ankle sock with a kit-colored stripe
    w = P["w_sh"][1] + 2.2 * R / 60
    s0 = A[1] - P["shin"] * 0.30
    sock = [(A[0] - w / 2, s0), (A[0] + w / 2, s0), (A[0] + w / 2 + 0.6, A[1] + 1), (A[0] - w / 2 - 0.6, A[1] + 1)]
    cv.shape(apl(shn, sock), dim(C(pal["sock"]), k), dim(C(pal["sock_sh"]), k), C(pal["sock_ln"]),
             lw * 0.9, shift=3.0 * R / 60)
    cv.polyline(apl(shn, [(A[0] - w / 2 + 0.6, s0 + 2.6 * R / 60), (A[0] + w / 2 - 0.6, s0 + 2.6 * R / 60)]),
                dim(C(pal["jersey"]), k), 1.8 * R / 60)
    # chunky sneaker (points forward, +x)
    f = P["foot_h"] / 0.70
    ax, ay = A
    shoe = catmull([(ax - 0.62 * f, ay + 0.74 * f), (ax - 0.72 * f, ay + 0.10 * f),
                    (ax - 0.48 * f, ay - 0.46 * f), (ax + 0.08 * f, ay - 0.42 * f),
                    (ax + 0.60 * f, ay - 0.14 * f), (ax + 1.08 * f, ay + 0.18 * f),
                    (ax + 1.20 * f, ay + 0.56 * f), (ax + 1.06 * f, ay + 0.76 * f)], n=6)
    shoe_w = apl(ft, shoe)
    cv.shape(shoe_w, dim(C(pal["shoe"]), k), dim(C(pal["shoe_sh"]), k), C(pal["sock_ln"]),
             lw * 0.9, shift=f * 0.24)
    sole = [(ax - 0.74 * f, ay + 0.50 * f), (ax + 1.24 * f, ay + 0.50 * f),
            (ax + 1.24 * f, ay + 0.80 * f), (ax - 0.74 * f, ay + 0.80 * f)]
    cv.shape(apl(ft, sole), dim(C(pal["sole"]), k), None, None, clip=[shoe_w])
    cv.polyline(apl(ft, [(ax - 0.66 * f, ay + 0.50 * f), (ax + 1.16 * f, ay + 0.50 * f)]),
                dim(C(pal["jersey"]), k), 1.6 * R / 60, clip=[shoe_w])
    cv.polyline(apl(ft, qbez((ax - 0.40 * f, ay + 0.26 * f), (ax + 0.16 * f, ay + 0.40 * f),
                             (ax + 0.72 * f, ay + 0.00 * f), n=8)), dim(C(pal["jersey"]), k), 2.0 * R / 60)
    for i in range(2):  # laces
        lx = ax + (0.02 + i * 0.22) * f
        cv.polyline(apl(ft, [(lx - 0.08 * f, ay - 0.36 * f + i * 0.10 * f), (lx + 0.12 * f, ay - 0.26 * f + i * 0.10 * f)]),
                    C(pal["sock_ln"]), 1.1 * R / 60)
    # shorts leg tube over the top of the thigh
    tube = [(H[0] - w2 / 2, H[1] - 4 * R / 60), (H[0] + w2 / 2, H[1] - 4 * R / 60),
            (H[0] + w2 / 2 + 0.6, H[1] + P["thigh"] * 0.38), (H[0] - w2 / 2 - 0.6, H[1] + P["thigh"] * 0.44)]
    cv.shape(apl(th, tube), dim(C(pal["shorts"]), k), dim(C(pal["shorts_sh"]), k),
             C(pal["jersey_ln"]), lw, shift=4.0 * R / 60)


def draw_lower_body(cv, M, P, pal, g):
    cx, waist_y, hip_y, R = g["cx"], g["waist_y"], g["hip_y"], g["R"]
    ww, hw, lw = P["waist_w"], P["hip_w"], P["lw"]
    root = M["root"]
    u = R / 60
    mid = apl(root, [(cx - ww * 0.52, waist_y - 6 * u), (cx + ww * 0.54, waist_y - 6 * u),
                     (cx + hw * 0.50, hip_y - 5 * u), (cx - hw * 0.50, hip_y - 5 * u)])
    cv.shape(mid, C(pal["skin"]), C(pal["skin_sh"]), C(pal["skin_ln"]), lw, shift=ww * 0.20)
    # occlusion under the crop-top hem
    hem_y = waist_y - 2 * u
    cv.shape(apl(M["chest"], [(cx - ww * 0.6, hem_y - u), (cx + ww * 0.6, hem_y - u),
                              (cx + ww * 0.6, hem_y + 4 * u), (cx - ww * 0.6, hem_y + 4 * u)]),
             C(pal["skin_sh"]), clip=[mid])
    my = (waist_y + hip_y) / 2
    cv.polyline(apl(root, [(cx + 3 * u, my - 2.0 * u), (cx + 3.4 * u, my + 1.8 * u)]), C(pal["skin_ln"]), 1.3 * u)
    sb = apl(root, [(cx - hw * 0.54, hip_y - 9 * u), (cx + hw * 0.54, hip_y - 9 * u),
                    (cx + hw * 0.58, hip_y + 13 * u), (cx + 3 * u, hip_y + 8 * u), (cx - hw * 0.58, hip_y + 13 * u)])
    cv.shape(sb, C(pal["shorts"]), C(pal["shorts_sh"]), C(pal["jersey_ln"]), lw, shift=hw * 0.20)
    # side stripe + waistband with drawstring
    cv.shape(apl(root, [(cx - hw * 0.50, hip_y - 6 * u), (cx - hw * 0.40, hip_y - 6 * u),
                        (cx - hw * 0.44, hip_y + 13 * u), (cx - hw * 0.56, hip_y + 13 * u)]),
             C(pal["trim"]), None, None, clip=[sb])
    band = apl(root, [(cx - hw * 0.54, hip_y - 9 * u), (cx + hw * 0.54, hip_y - 9 * u),
                      (cx + hw * 0.545, hip_y - 5.4 * u), (cx - hw * 0.545, hip_y - 5.4 * u)])
    cv.shape(band, C(pal["trim"]), C(pal["trim_sh"]), C(pal["jersey_ln"]), lw * 0.8, shift=1.5 * u)
    for dx in (-1.6, 1.6):
        cv.polyline(apl(root, [(cx + 4 * u, hip_y - 6 * u), (cx + (4 + dx) * u, hip_y - 1 * u)]),
                    C(pal["trim"]), 1.2 * u)


def draw_jersey(cv, M, P, pal, g, ch):
    cx, sh_y, waist_y, R = g["cx"], g["sh_y"], g["waist_y"], g["R"]
    sw, cw, ww, tu, lw = P["shoulder_w"], P["chest_w"], P["waist_w"], P["torso_up"], P["lw"]
    u = R / 60
    chest = M["chest"]
    ln = C(pal["jersey_ln"])
    hem_y = waist_y - 2 * u
    neck_l = qbez((cx - sw * 0.30, sh_y - u), (cx - sw * 0.10, sh_y + tu * 0.30), (cx + 3 * u, sh_y + tu * 0.26), 10)
    neck_r = qbez((cx + 3 * u, sh_y + tu * 0.26), (cx + sw * 0.16, sh_y + tu * 0.22), (cx + sw * 0.30, sh_y - u), 10)
    far_arm = qbez((cx + sw * 0.40, sh_y - u), (cx + sw * 0.36, sh_y + tu * 0.28), (cx + cw * 0.52, sh_y + tu * 0.30), 8)
    far_side = catmull([(cx + cw * 0.52, sh_y + tu * 0.30), (cx + cw * 0.51, sh_y + tu * 0.52),
                        (cx + ww * 0.53, hem_y - tu * 0.12), (cx + ww * 0.52, hem_y)], n=6)
    hem = qbez((cx + ww * 0.52, hem_y), (cx, hem_y + 3 * u), (cx - ww * 0.54, hem_y), 10)
    near_arm = qbez((cx - cw * 0.54, sh_y + tu * 0.36), (cx - sw * 0.44, sh_y + tu * 0.22), (cx - sw * 0.42, sh_y - u), 8)
    jp = apl(chest, neck_l + neck_r + [(cx + sw * 0.40, sh_y - u)] + far_arm + far_side + hem + near_arm)
    ys = [p[1] for p in jp]
    cv.shape(jp, Grad(pal["jersey_top"], pal["jersey"], min(ys), max(ys)), C(pal["jersey_sh"]), ln, lw,
             shift=cw * 0.22)
    # side panel stripe down the far side
    stripe = [(cx + cw * 0.30, sh_y + tu * 0.40), (cx + cw * 0.58, sh_y + tu * 0.24),
              (cx + ww * 0.62, hem_y + 3 * u), (cx + ww * 0.32, hem_y + 3 * u)]
    cv.shape(apl(chest, stripe), C(pal["trim"]), C(pal["trim_sh"]), None, clip=[jp], shift=2 * u)
    cv.polyline(apl(chest, neck_l + neck_r), C(pal["trim"]), lw * 1.05)
    cv.polyline(apl(chest, qbez((cx + ww * 0.50, hem_y - 1.6 * u), (cx, hem_y + 1.4 * u),
                                (cx - ww * 0.52, hem_y - 1.6 * u), 10)), C(pal["trim"]), lw * 1.0)
    cv.polyline(apl(chest, near_arm), C(pal["trim"]), lw * 0.9)
    cv.polyline(apl(chest, far_arm), C(pal["trim"]), lw * 0.9)
    cv.text(ch["number"], ap(chest, (cx + 1 * u, sh_y + tu * 0.62)), tu * 0.60, mrot(chest),
            C(pal["trim"]), ln, lw * 0.55, sx=0.84, clip=[jp])


def draw_neck(cv, M, P, pal, g):
    R = g["R"]
    nw = R * 0.30
    base = (g["cx"] + 2 * R / 60, g["sh_y"] + 6 * R / 60)
    top = (g["hx"] + R * 0.08, g["chin_y"] - R * 0.30)
    poly = apl(M["neck"], capsule(base, nw * 1.1, top, nw))
    cv.shape(poly, C(pal["skin"]), C(pal["skin_sh"]), C(pal["skin_ln"]), P["lw"], shift=nw * 0.5)
    return poly


# ============================================================ head drawing
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


def draw_extras(cv, Mh, extras, pal, g, lw, stage):
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
        for a in (0.4, 2.5, 4.4):
            px, py = ox + 0.82 * R * math.cos(a), oy + 0.20 * R * math.sin(a)
            cv.shape(X(star(px, py, 0.11 * R, 5, 0.45)), C(pal["spark"]), None, C(pal["spark_ln"]), lw * 0.5)


# ================================================================== hair
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
    key = {"ponytail": "short", "twintails": "short", "bob": "bob", "long": "long", "buns": "buns"}[style]
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


# ============================================================= accessories
def bow(cv, p, s, col, sh, ln, lw, ang=0.0):
    for sgn in (-1, 1):
        cv.shape(rell(p[0] + sgn * 0.88 * s, p[1] - 0.10 * s, 0.86 * s, 0.56 * s, sgn * 0.35 + ang, 24),
                 C(col), C(sh), C(ln), lw * 0.8, shift=0.25 * s)
        tail = [(p[0] + sgn * 0.15 * s, p[1]), (p[0] + sgn * 0.62 * s, p[1] + 1.10 * s),
                (p[0] + sgn * 0.30 * s, p[1] + 1.02 * s), (p[0] + sgn * 0.02 * s, p[1] + 0.30 * s)]
        cv.shape(tail, C(col), C(sh), C(ln), lw * 0.7, shift=0.2 * s)
    cv.shape(ell(p[0], p[1], 0.36 * s, 0.34 * s, n=20), C(col), C(sh), C(ln), lw * 0.8, shift=0.12 * s)


def draw_accessory(cv, Mh, g, pal, P, ch, roots):
    R, hx, hy, lw = g["R"], g["hx"], g["hy"], P["lw"]
    X = lambda pts: apl(Mh, pts)
    acc = ch["acc"]
    if acc == "scrunchie" and roots:
        r = roots[0]
        cv.shape(fluffy(r[0], r[1], 0.18 * R, 0.14 * R, 0, math.tau, 8, 0.10, n=64)[:-1],
                 C(pal["jersey"]), C(pal["jersey_sh"]), C(pal["jersey_ln"]), lw * 0.9, shift=0.06 * R)
    elif acc == "ribbons":
        for r in roots:
            bow(cv, r, 0.20 * R, pal["jersey"], pal["jersey_sh"], pal["jersey_ln"], lw)
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
        cv.shape(band, C(pal["jersey"]), C(pal["jersey_sh"]), C(pal["jersey_ln"]), lw * 0.85, shift=0.05 * R)
        cv.polyline(X(line), C(pal["trim"]), R * 0.03, clip=[band])


# =================================================================== ball/fx
def draw_ball(cv, c, r, pal, lw):
    body = ell(c[0], c[1], r, r, n=40)
    cv.shape(body, Grad(pal["ball_top"], pal["ball"], c[1] - r, c[1] + r * 0.4), C(pal["ball_sh"]),
             C(pal["ball_ln"]), lw, shift=r * 0.40)
    ln = C(pal["ball_ln"])
    cv.polyline(ell(c[0], c[1], r * 0.34, r, -math.pi / 2, math.pi / 2, 16), ln, lw * 0.55, clip=[body])
    cv.polyline([(c[0] - r, c[1] + r * 0.05), (c[0], c[1] - r * 0.06), (c[0] + r, c[1] + r * 0.05)],
                ln, lw * 0.55, clip=[body])
    cv.polyline(ell(c[0] - r * 1.05, c[1], r * 0.62, r * 0.92, -1.1, 1.1, 14), ln, lw * 0.55, clip=[body])
    cv.polyline(ell(c[0] + r * 1.05, c[1], r * 0.62, r * 0.92, math.pi - 1.1, math.pi + 1.1, 14),
                ln, lw * 0.55, clip=[body])
    cv.shape(ell(c[0] - r * 0.36, c[1] - r * 0.42, r * 0.26, r * 0.15, n=16), C((255, 240, 220)),
             clip=[body], alpha=170)


def flame(bx, by, wd, ht, lean):
    tip = (bx + lean, by - ht)
    pts = bez((bx - wd / 2, by), (bx - wd * 0.62, by - ht * 0.45), (bx + lean * 0.4 - wd * 0.2, by - ht * 0.78), tip, 14)
    pts += bez(tip, (bx + lean * 0.4 + wd * 0.26, by - ht * 0.70), (bx + wd * 0.62, by - ht * 0.40), (bx + wd / 2, by), 14)
    pts += ell(bx, by, wd / 2, wd * 0.28, 0, math.pi, 10)
    return pts


def fx_layer(kind, w, h, g, P, char_img, anchor=None):
    """Effects that sit BEHIND the character (no sticker stroke)."""
    cv = Canvas(w, h)
    R, cx = g["R"], g["cx"]
    if kind == "fire":
        base_y = g["floor"] + 2
        for i, (dx, ht, wd, lean) in enumerate(((-58, 130, 44, -14), (58, 140, 46, 16), (-32, 205, 54, -6),
                                                 (34, 215, 56, 8), (0, 255, 66, 4), (-80, 90, 34, -20),
                                                 (82, 96, 36, 20))):
            pts = flame(cx + dx * R / 60, base_y, wd * R / 60, ht * R / 60, lean * R / 60)
            cv.shape(pts, Grad((255, 70, 30), (255, 226, 110), base_y - ht * R / 60, base_y), alpha=225)
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


# ============================================================ expressions
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
}


# ================================================================== poses
def make_pose(name, J, bones, P, g, t=0.0, variant=None):
    """Returns (pose, ball_center_or_None, default_expr, fx_kind, fx_anchor)."""
    R, hx, hy, cx, floor = g["R"], g["hx"], g["hy"], g["cx"], g["floor"]
    br = P["ball_r"]
    u = R / 60

    def head_pt(pose, x, y):
        return ap(solve(bones, pose)["head"], (hx + x * R, hy + y * R))

    ph = t * math.tau
    ball, expr, fx, anchor = None, None, None, None
    if name == "idle":
        sw = math.sin(ph)
        pose = {"_t": (0, -0.8 * u * sw), "chest": -2 + 1.2 * sw, "head": 4 + 2.0 * math.sin(ph - 0.6),
                "n_up": 17 + 2 * sw, "n_lo": -12, "f_up": -13 - 2 * sw, "f_lo": 12,
                "n_th": -3, "n_sh": 3, "f_th": 4,
                "hair": (6 + 4 * math.sin(ph - 1.0), 6 + 3 * math.sin(ph - 1.6), 8 + 3 * math.sin(ph - 2.2))}
        v = variant or "relaxed"
        if v == "hip":   # near hand planted on the hip, elbow out
            M0 = solve(bones, pose)
            pose["ik_n"] = (ap(M0["root"], (cx - P["hip_w"] * 0.58, g["waist_y"] + 7 * u)), 1.0, 1.25)
        elif v == "peace":   # V sign beside the cheek
            pose["ik_n"] = (head_pt(pose, -1.02, 0.62 + 0.03 * sw), -1.0, 1.4)
            pose["hand_n"], pose["arm_front"] = "peace", True
        elif v == "wave":
            pose["ik_f"] = (head_pt(pose, 1.22, 0.22 + 0.08 * math.sin(2 * ph)), 1.0, 1.45)
        elif v == "cheer":
            pose["ik_n"] = (head_pt(pose, -1.16, 0.40 + 0.04 * sw), -1.0, 1.35)
            pose["ik_f"] = (head_pt(pose, 1.18, 0.34 - 0.04 * sw), 1.0, 1.4)
            pose["arm_front"] = True
        elif v == "fist":   # 'ganbare!' — fist pump + fist at the chest
            pose["ik_f"] = (head_pt(pose, 1.12, 0.12 + 0.05 * sw), 1.0, 1.45)
            M0 = solve(bones, pose)
            pose["ik_n"] = (ap(M0["chest"], (cx - 2 * u, g["sh_y"] + 20 * u)), 1.0, 1.2)
            pose["hand_n"] = pose["hand_f"] = "fist"
        if 0.62 <= t % 1.0 < 0.70:
            expr = "blink"
    elif name in ("run", "dribble"):
        still = name == "dribble"
        s1 = math.sin(ph)
        pose = {"_t": (0, (-3 - 5 * abs(s1)) * u), "root": 3, "chest": 9 + 1.5 * math.cos(2 * ph),
                "head": -8 - 1.5 * math.cos(2 * ph),
                "n_th": -34 * s1, "f_th": 34 * s1,
                "n_sh": 14 + 50 * max(0.0, math.cos(ph)), "f_sh": 14 + 50 * max(0.0, -math.cos(ph)),
                "n_ft": -10 * s1, "f_ft": 10 * s1, "n_up": 38 * s1, "n_lo": -55,
                "hair": (24 + 10 * math.sin(ph - 0.9), -6 + 8 * math.sin(ph - 1.6), -12 + 9 * math.sin(ph - 2.3))}
        if still:   # hand meeting the ball at the top of the bounce, mid-stride
            pose.update({"n_th": -28, "n_sh": 30, "n_ft": -8, "f_th": 26, "f_sh": 52, "f_ft": 10,
                         "n_up": 30, "_t": (0, -6 * u)})
        b = 1.0 if still else abs(math.cos(ph))
        H = 66 * u
        ball = (cx + 52 * u, floor - br - 5 * u - (H - br - 5 * u) * b ** 1.4)
        hand_top = floor - H - br - 3 * u
        pose["ik_f"] = ((ball[0] - 3 * u, hand_top + 10 * u * (1 - b)), 1.0, 1.25)
        expr = "smile"
        fx = "speed"
    elif name == "jump_shot":
        pose = {"_t": (0, -46 * u), "root": -3, "chest": -5, "head": -10,
                "n_th": -28, "n_sh": 50, "n_ft": -10, "f_th": 6, "f_sh": 34, "f_ft": 6, "hair": (16, 10, 6)}
        ball = head_pt(pose, 1.02 + br / R * 0.3, 0.26)
        pose["ik_f"] = ((ball[0] - 3 * u, ball[1] + br * 0.85), 1.0, 1.45)
        pose["ik_n"] = (head_pt(pose, -1.18, 0.62), -1.0, 1.3)
        expr = "focus"
    elif name == "dunk":
        pose = {"_t": (6 * u, -62 * u), "root": 8, "chest": 14, "head": -8,
                "n_th": -44, "n_sh": 72, "n_ft": -14, "f_th": 20, "f_sh": 64, "f_ft": 14,
                "n_up": 64, "n_lo": -34, "hair": (78, 16, 10)}
        M0 = solve(bones, pose)
        S = ap(M0["chest"], J["sh_f"])
        hand = (S[0] + 50 * u, S[1] + 14 * u)
        pose["ik_f"] = (hand, 1.0, 1.3)
        ball = (hand[0] + 8 * u, hand[1] + br + 9 * u)
        expr, fx, anchor = "shout", "burst", ball
    elif name == "block":
        pose = {"_t": (0, -40 * u), "chest": -4, "head": -4,
                "n_th": -10, "n_sh": 40, "f_th": 10, "f_sh": 46, "hair": (12, 8, 6), "arm_front": True}
        pose["ik_n"] = (head_pt(pose, -1.14, 0.20), -1.0, 1.45)
        pose["ik_f"] = (head_pt(pose, 1.16, 0.40), 1.0, 1.45)
        expr = "shout"
    elif name == "steal":
        pose = {"_t": (8 * u, 5 * u), "root": 12, "chest": 14, "head": -12,
                "n_th": -50, "n_sh": 56, "n_ft": -6, "f_th": 36, "f_sh": 14, "f_ft": 16,
                "f_up": 44, "f_lo": -30, "hair": (40, 4, -8)}
        target = (cx + 82 * u, floor - 74 * u)
        pose["ik_n"] = (target, 1.0, 1.5)
        expr, fx, anchor = "smug", "swoosh", target
    elif name == "hurt":
        pose = {"_t": (-6 * u, 54 * u), "root": -12, "chest": -6, "head": 10,
                "n_th": -76, "n_sh": 14, "n_ft": -30, "f_th": -66, "f_sh": 26, "f_ft": -24, "hair": (-10, 4, 8)}
        pose["ik_n"] = ((cx - 40 * u, floor - 6 * u), 1.0, 1.4)
        pose["ik_f"] = ((cx - 6 * u, floor - 4 * u), 1.0, 1.4)
        expr = "dizzy"
    elif name in ("celebrate", "hop"):
        hop = abs(math.sin(math.pi * t)) if name == "hop" else 0.75
        pose = {"_t": (0, -24 * u * hop), "chest": -3, "head": 8 + 3 * math.sin(ph),
                "n_th": -8, "n_sh": 6 + 20 * hop, "f_th": 20, "f_sh": 66, "f_ft": 12,
                "hair": (-16 + 24 * math.cos(ph), -8 + 10 * math.cos(ph - 0.7), -4 + 8 * math.cos(ph - 1.4)),
                "arm_front": True}
        wave = 0.06 * math.sin(ph * 2)
        pose["ik_n"] = (head_pt(pose, -1.16, 0.40 + wave), -1.0, 1.35)
        pose["ik_f"] = (head_pt(pose, 1.18, 0.34 - wave), 1.0, 1.4)
        expr = "joy"
    elif name == "on_fire":
        pose = {"_t": (0, 4 * u), "chest": 4, "head": -4,
                "n_th": -16, "n_sh": 22, "n_ft": -6, "f_th": 14, "f_sh": 18, "f_ft": 6, "hair": (38, 10, -6)}
        pose["ik_f"] = (head_pt(pose, 1.12, 0.36), 1.0, 1.4)
        M0 = solve(bones, pose)
        pose["ik_n"] = (ap(M0["chest"], (cx + 8 * u, g["sh_y"] + 22 * u)), 1.0, 1.2)
        expr, fx = "fired_up", "fire"
    else:
        raise ValueError("unknown pose %r" % name)
    return pose, ball, expr, fx, anchor


# ================================================================= render
def render(cid, pose_name="idle", expr_name=None, t=0.0, scale=1.0, w=360, h=480, cx=None,
           floor=None, fx=True, shadow=True, variant=None):
    ch = CAST[cid]
    pal = palette(cid)
    P = body_params(scale, cx=cx if cx is not None else BODY["cx"] * scale,
                    floor=floor if floor is not None else BODY["floor"] * scale)
    J, bones, g = build(P)
    pose, ball, pose_expr, fx_kind, anchor = make_pose(pose_name, J, bones, P, g, t, variant or ch.get("idle"))
    ex = EXPR[expr_name or pose_expr or ch["signature"]]
    M = solve(bones, pose)
    arms = {s: arm_joints(M, J, P, pose, s) for s in ("n", "f")}
    Mh = M["head"]
    R, lw = g["R"], P["lw"]
    hair_ang = pose.get("hair", (6, 6, 8))
    cv = Canvas(w, h)

    if ch["style"] == "long":
        draw_long_back(cv, Mh, g, pal, P, hair_ang)
    roots = draw_tails(cv, Mh, g, pal, P, ch["style"], hair_ang)
    draw_arm(cv, arms["f"], P, pal, far=True, band=False, hand=pose.get("hand_f", "mitten"))
    draw_leg(cv, M, J, P, pal, "f", far=True)
    back = bob_poly(g["hx"], g["hy"], R) if ch["style"] == "bob" else cap_poly(g["hx"], g["hy"], R)
    cv.shape(apl(Mh, back), Grad(pal["hair_sh"], pal["hair_bot"], g["hy"] - R, g["hy"] + R),
             C(dim(C(pal["hair_sh"]), 0.80)), C(pal["hair_ln"]), lw, shift=R * 0.12)
    if ch["style"] == "buns":
        draw_buns(cv, Mh, g, pal, P)
    if ch["acc"] in ("scrunchie", "ribbons"):
        draw_accessory(cv, Mh, g, pal, P, ch, roots)
    draw_lower_body(cv, M, P, pal, g)
    draw_leg(cv, M, J, P, pal, "n", far=False)
    neck = draw_neck(cv, M, P, pal, g)
    draw_jersey(cv, M, P, pal, g, ch)
    if not pose.get("arm_front"):
        draw_arm(cv, arms["n"], P, pal, far=False, band=True, hand=pose.get("hand_n", "mitten"))

    # ---- face
    hx, hy = g["hx"], g["hy"]
    X = lambda pts: apl(Mh, pts)
    outline = face_outline(hx, hy, R)
    cv.shape(X([(x, y + R * 0.20) for x, y in outline]), C(pal["skin_sh"]), clip=[neck])
    cv.shape(X([(x, y + R * 0.09) for x, y in outline]), C(pal["skin_sh2"]), clip=[neck])
    face = X(outline)
    cv.shape(face, Grad(pal["skin_top"], pal["skin"], hy - R, hy + R), C(pal["skin_sh"]), C(pal["skin_ln"]),
             lw, shift=R * 0.15)
    bp_local = bangs_poly(hx, hy, R, ch["bangs"])
    cv.shape(X([(x, y + R * 0.12) for x, y in bp_local]), C(pal["skin_sh"]), clip=[face])
    cv.shape(X([(x, y + R * 0.05) for x, y in bp_local]), C(pal["skin_sh2"]), clip=[face])
    cv.blob(X(ell(hx - 0.46 * R, hy + 0.60 * R, 0.17 * R, 0.085 * R, n=24)), C(pal["blush"], 125), R * 0.05)
    cv.blob(X(ell(hx + 0.54 * R, hy + 0.58 * R, 0.11 * R, 0.07 * R, n=24)), C(pal["blush"], 105), R * 0.05)
    cv.shape(X(ell(hx - 0.52 * R, hy + 0.52 * R, 0.05 * R, 0.03 * R, n=12)), C((255, 255, 255)), alpha=150)
    eyes = ex["eyes"] if isinstance(ex["eyes"], tuple) else (ex["eyes"], ex["eyes"])
    draw_eye(cv, Mh, "near", eyes[0], pal, g, lw, ch["tilt"])
    draw_eye(cv, Mh, "far", eyes[1], pal, g, lw, ch["tilt"])
    cv.polyline(X([(hx + 0.24 * R, hy + 0.53 * R), (hx + 0.27 * R, hy + 0.56 * R)]), C(pal["skin_ln"]), R * 0.028)
    draw_mouth(cv, Mh, ex["mouth"], pal, g, lw)
    draw_extras(cv, Mh, ex.get("extras", []), pal, g, lw, "face")

    # ---- front hair, accessories, brows, FX marks
    draw_front_hair(cv, Mh, g, pal, P, ch)
    if ch["acc"] not in ("scrunchie", "ribbons"):
        draw_accessory(cv, Mh, g, pal, P, ch, roots)
    draw_brows(cv, Mh, ex["brows"], pal, g)
    draw_extras(cv, Mh, ex.get("extras", []), pal, g, lw, "top")
    if pose.get("arm_front"):
        draw_arm(cv, arms["n"], P, pal, far=False, band=True, hand=pose.get("hand_n", "mitten"))
    if ball is not None:
        draw_ball(cv, ball, P["ball_r"], pal, lw * 0.9)
    cv.outline_pass(OUTLINE, P["stroke"])
    char = cv.finish()

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        lift = -pose.get("_t", (0, 0))[1] / (R / 60)
        sc = max(0.5, 1.0 - max(0.0, lift) / 150.0)
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sx = g["cx"] + pose.get("_t", (0, 0))[0] + 4 * scale
        ImageDraw.Draw(sh).ellipse([sx - P["hip_w"] * 1.05 * sc, g["floor"] - 6 * scale * sc,
                                    sx + P["hip_w"] * 1.05 * sc, g["floor"] + 6 * scale * sc],
                                   fill=(20, 10, 40, 130))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2.5 * scale)))
    if fx and fx_kind:
        out.alpha_composite(fx_layer(fx_kind, w, h, g, P, char, anchor))
    out.alpha_composite(char)
    return out


def render_head(cid, expr_name, size=340, scale=1.5, pose="idle"):
    """Face close-up: the same rig scaled up, framed on the head."""
    R = BODY["head_r"] * scale
    hx_target, hy_target = size * 0.50, size * 0.60
    cx = hx_target - 0.10 * R
    chin = hy_target + 0.98 * R
    P = body_params(scale)
    floor = chin + P["neck"] + P["torso_up"] + P["torso_low"] + P["thigh"] + P["shin"] + P["foot_h"]
    return render(cid, pose, expr_name, scale=scale, w=size, h=size, cx=cx, floor=floor, fx=False,
                  shadow=False, variant="relaxed")


# ================================================================= sheets
def court_bg(w, h, floor=432):
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(bg)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=(int(32 + 26 * k), int(22 + 14 * k), int(56 + 20 * k), 255))
    d.rectangle([0, floor, w, h], fill=(198, 140, 82, 255))
    for x in range(-60, w + 60, 46):
        d.line([(x, floor), (x - 36, h)], fill=(180, 124, 70, 255), width=2)
    d.line([(0, floor), (w, floor)], fill=(238, 232, 224, 255), width=3)
    return bg


def pastel_bg(w, h, c0, c1):
    bg = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(bg)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=C(mix(c0, c1, y / h)))
    return bg


def label(d, xy, text, size, fill, anchor="la"):
    d.text(xy, text, font=font(size), fill=fill, anchor=anchor)


def sheet_roster(out):
    order = ["aki", "yumi", "rin", "hana", "miko"]
    pw, ph, top = 360, 480, 70
    sheet = Image.new("RGBA", (pw * len(order), ph + top + 64), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "ABSOLUTE BALLERS — the cast (one rig, five girls)", 30, (255, 214, 92, 255))
    for i, cid in enumerate(order):
        ch = CAST[cid]
        p = court_bg(pw, ph, floor=446)
        p.alpha_composite(render(cid, "idle", ch["signature"], scale=1.3, cx=172, floor=446))
        sheet.alpha_composite(p, (i * pw, top))
        col = C(ch["kit"]) if sum(ch["kit"]) > 200 else C(ch.get("trim", (255, 255, 255)))
        label(d, (i * pw + pw // 2, top + ph + 8), ch["name"], 26, col, "ma")
        label(d, (i * pw + pw // 2, top + ph + 38), ch["tag"], 16, (220, 214, 240, 255), "ma")
    sheet.convert("RGB").save(out)
    return out


def sheet_expressions(out, cid="aki"):
    names = ["smile", "joy", "focus", "smug", "wink", "surprised", "fired_up", "pout", "dizzy", "teary"]
    cell, lab, cols, top = 300, 34, 5, 70
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cell * cols, top + rows * (cell + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "%s — expression set (same face rig, swapped layers)" % CAST[cid]["name"], 30,
          (255, 214, 92, 255))
    tint = CAST[cid]["kit"]
    for i, n in enumerate(names):
        x, y = (i % cols) * cell, top + (i // cols) * (cell + lab)
        bg = pastel_bg(cell, cell, mix(tint, (255, 255, 255), 0.78), mix(tint, (255, 255, 255), 0.50))
        bg.alpha_composite(render_head(cid, n, size=cell))
        sheet.alpha_composite(bg, (x, y))
        label(d, (x + cell // 2, y + cell + 6), n.replace("_", " ").upper(), 18, (232, 226, 255, 255), "ma")
    sheet.convert("RGB").save(out)
    return out


PORTRAITS = {
    "aki": ["smile", "joy", "fired_up", "pout"],
    "yumi": ["wink", "joy", "teary", "surprised"],
    "rin": ["smug", "focus", "pout", "surprised"],
    "hana": ["joy", "smile", "teary", "dizzy"],
    "miko": ["fired_up", "joy", "smug", "effort"],
}


def sheet_portraits(out):
    cell, lab, top, name_w = 230, 28, 70, 150
    order = ["aki", "yumi", "rin", "hana", "miko"]
    cols = len(PORTRAITS["aki"])
    sheet = Image.new("RGBA", (name_w + cell * cols, top + len(order) * (cell + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "The cast — each girl's expression range", 30, (255, 214, 92, 255))
    scale = 1.5 * cell / 340
    for r, cid in enumerate(order):
        ch = CAST[cid]
        y = top + r * (cell + lab)
        col = C(ch["kit"]) if sum(ch["kit"]) > 200 else C(ch.get("trim", (255, 255, 255)))
        label(d, (name_w // 2, y + cell // 2 - 12), ch["name"], 30, col, "mm")
        label(d, (name_w // 2, y + cell // 2 + 20), ch["tag"], 12, (200, 194, 226, 255), "mm")
        for c, ex in enumerate(PORTRAITS[cid]):
            x = name_w + c * cell
            bg = pastel_bg(cell, cell, mix(ch["kit"], (255, 255, 255), 0.80), mix(ch["kit"], (255, 255, 255), 0.52))
            bg.alpha_composite(render_head(cid, ex, size=cell, scale=scale))
            sheet.alpha_composite(bg, (x, y))
            label(d, (x + cell // 2, y + cell + 4), ex.replace("_", " ").upper(), 15, (232, 226, 255, 255), "ma")
    sheet.convert("RGB").save(out)
    return out


def sheet_actions(out, cid="aki"):
    poses = [("dribble", "DRIBBLE"), ("jump_shot", "JUMP SHOT"), ("dunk", "SLAM DUNK"), ("block", "BLOCK"),
             ("steal", "STEAL"), ("hurt", "KNOCKED DOWN"), ("celebrate", "CELEBRATE"), ("on_fire", "ON FIRE")]
    pw, ph, lab, cols, top = 360, 480, 34, 4, 70
    sheet = Image.new("RGBA", (pw * cols, top + 2 * (ph + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "%s — move set (poses are just bone angles + IK targets)" % CAST[cid]["name"], 30,
          (255, 214, 92, 255))
    for i, (pose, title) in enumerate(poses):
        x, y = (i % cols) * pw, top + (i // cols) * (ph + lab)
        p = court_bg(pw, ph)
        p.alpha_composite(render(cid, pose))
        sheet.alpha_composite(p, (x, y + lab))
        label(d, (x + 12, y + 6), title, 18, (232, 226, 255, 255))
    sheet.convert("RGB").save(out)
    return out


def anim_gif(out, frames=16):
    clips = [("aki", "run", None), ("yumi", "idle", None), ("miko", "hop", None)]
    pw, ph = 360, 480
    imgs = []
    for f in range(frames):
        t = f / frames
        frame = Image.new("RGBA", (pw * len(clips), ph), (0, 0, 0, 255))
        for i, (cid, pose, ex) in enumerate(clips):
            p = court_bg(pw, ph)
            p.alpha_composite(render(cid, pose, ex, t=t))
            frame.alpha_composite(p, (i * pw, 0))
        imgs.append(frame.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT))
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=70, loop=0, optimize=False, disposal=2)
    return out


def main(argv):
    if len(argv) >= 2 and argv[0] == "showcase":
        d = argv[1]
        os.makedirs(d, exist_ok=True)
        for fn in (lambda: sheet_roster(os.path.join(d, "cast_roster.png")),
                   lambda: sheet_expressions(os.path.join(d, "expressions_aki.png")),
                   lambda: sheet_portraits(os.path.join(d, "cast_portraits.png")),
                   lambda: sheet_actions(os.path.join(d, "moveset_aki.png")),
                   lambda: anim_gif(os.path.join(d, "animated_preview.gif"))):
            print("wrote", fn())
        return 0
    if len(argv) >= 5 and argv[0] == "one":
        _, cid, pose, ex, out = argv[:5]
        bg = court_bg(360, 480)
        bg.alpha_composite(render(cid, pose, None if ex == "-" else ex))
        bg.convert("RGB").save(out)
        print("wrote", out)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
