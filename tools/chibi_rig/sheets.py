"""Showcase sheets for docs/art: roster, portraits, expressions, move set, GIF."""


from PIL import Image, ImageDraw

from .paint import C, font, mix
from .cast import CAST
from .render import render, render_head


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


ORDER = list(CAST)


def name_color(ch):
    """Her kit color for labels, unless it's too dark to read on the sheet."""
    kit = ch["kit"]
    if 0.299 * kit[0] + 0.587 * kit[1] + 0.114 * kit[2] >= 110:
        return C(kit)
    return C(ch["trim"]) if "trim" in ch else C(mix(kit, (255, 255, 255), 0.55))


def sheet_roster(out, cols=5):
    pw, ph, lab, top = 360, 480, 64, 70
    rows = (len(ORDER) + cols - 1) // cols
    sheet = Image.new("RGBA", (pw * cols, top + rows * (ph + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "ABSOLUTE BALLERS — the cast (one rig, %d girls)" % len(ORDER), 30, (255, 214, 92, 255))
    for i, cid in enumerate(ORDER):
        ch = CAST[cid]
        x, y = (i % cols) * pw, top + (i // cols) * (ph + lab)
        p = court_bg(pw, ph, floor=446)
        p.alpha_composite(render(cid, "idle", ch["signature"], scale=1.3, cx=172, floor=446))
        sheet.alpha_composite(p, (x, y))
        label(d, (x + pw // 2, y + ph + 8), ch["name"], 26, name_color(ch), "ma")
        label(d, (x + pw // 2, y + ph + 38), ch["tag"], 16, (220, 214, 240, 255), "ma")
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
    "sora": ["focus", "smile", "surprised", "pout"],
    "kaede": ["cool", "smug", "fired_up", "teary"],
    "nao": ["cheeky", "joy", "effort", "dizzy"],
    "tsuki": ["cool", "smile", "focus", "surprised"],
    "rei": ["shout", "cheeky", "joy", "pout"],
}


def sheet_portraits(out, groups=2):
    cell, lab, top, name_w = 230, 28, 70, 150
    cols = len(PORTRAITS["aki"])
    block_w = name_w + cell * cols
    per = (len(ORDER) + groups - 1) // groups
    sheet = Image.new("RGBA", (block_w * groups + 20 * (groups - 1), top + per * (cell + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "The cast — each girl's expression range", 30, (255, 214, 92, 255))
    scale = 1.5 * cell / 340
    for i, cid in enumerate(ORDER):
        ch = CAST[cid]
        x0, y = (i // per) * (block_w + 20), top + (i % per) * (cell + lab)
        label(d, (x0 + name_w // 2, y + cell // 2 - 12), ch["name"], 30, name_color(ch), "mm")
        label(d, (x0 + name_w // 2, y + cell // 2 + 20), ch["tag"], 12, (200, 194, 226, 255), "mm")
        for c, ex in enumerate(PORTRAITS[cid]):
            x = x0 + name_w + c * cell
            bg = pastel_bg(cell, cell, mix(ch["kit"], (255, 255, 255), 0.80), mix(ch["kit"], (255, 255, 255), 0.52))
            bg.alpha_composite(render_head(cid, ex, size=cell, scale=scale))
            sheet.alpha_composite(bg, (x, y))
            label(d, (x + cell // 2, y + cell + 4), ex.replace("_", " ").upper(), 15, (232, 226, 255, 255), "ma")
    sheet.convert("RGB").save(out)
    return out


# (move, title, t, variant): one-shot moves shown at their key moment
ACTIONS = [("dribble", "DRIBBLE", 0.0, "still"), ("jump_shot", "JUMP SHOT", 0.75, None),
           ("dunk", "SLAM DUNK", 0.6, None), ("block", "BLOCK", 2 / 3, None),
           ("steal", "STEAL", 1 / 3, None), ("hurt", "KNOCKED DOWN", 1.0, None),
           ("celebrate", "CELEBRATE", 0.3, "cheer"), ("on_fire", "ON FIRE", 0.0, None)]


def sheet_actions(out, cid="aki"):
    pw, ph, lab, cols, top = 360, 480, 34, 4, 70
    sheet = Image.new("RGBA", (pw * cols, top + 2 * (ph + lab)), (16, 11, 28, 255))
    d = ImageDraw.Draw(sheet)
    label(d, (20, 18), "%s — move set (poses are just bone angles + IK targets)" % CAST[cid]["name"], 30,
          (255, 214, 92, 255))
    for i, (pose, title, t, variant) in enumerate(ACTIONS):
        x, y = (i % cols) * pw, top + (i // cols) * (ph + lab)
        p = court_bg(pw, ph)
        p.alpha_composite(render(cid, pose, t=t, variant=variant))
        sheet.alpha_composite(p, (x, y + lab))
        label(d, (x + 12, y + 6), title, 18, (232, 226, 255, 255))
    sheet.convert("RGB").save(out)
    return out


def anim_gif(out, frames=16):
    clips = [("aki", "dribble", None), ("yumi", "idle", None), ("miko", "celebrate", None)]
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
