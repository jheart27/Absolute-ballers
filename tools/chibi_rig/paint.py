"""Supersampled canvas + color helpers: fills, cel shadows, unioned silhouettes,
lines, text, and the sticker outline pass."""

import colorsys
import os
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


SS = 4                      # supersampling factor


LIGHT = (-0.55, -0.83)      # light from the upper-left


OUTLINE = (42, 24, 52)      # sticker stroke around the whole character


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
            a = im.getchannel("A")
            for c in clip:
                m = Image.new("L", im.size, 0)
                ImageDraw.Draw(m).polygon([(px * SS - x, py * SS - y) for px, py in c], fill=255)
                a = ImageChops.multiply(a, m)
            im.putalpha(a)
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

    def finish(self, resample=Image.LANCZOS):
        """Downsample to final size. LANCZOS is crisper; BOX (plain area
        average) never rings, so it keeps the result linear in every color —
        the game bake needs that to separate the team kit exactly."""
        return self.img.resize((self.w, self.h), resample)


@lru_cache(maxsize=None)
def font(size):
    for p in ("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
              "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()
