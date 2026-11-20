"""Poses: every move as bone angles + IK targets, one function per move.

Conventions (offsets are in rig units u = head_r / 60, so poses scale):
  * angles in degrees; + swings a hanging limb backward (toward -x)
  * '_t'    in-place body offset (crouch, bob, sit, in-sprite hop)
  * '_air'  jump height, applied only to previews (lift=True). The game lifts
            sprites itself, so baked frames leave it out.
  * IK targets: ik_n / ik_f = (space, x, y, elbow_bend, max_stretch), space =
        head    x, y in head radii from the head center (follows the head)
        chest   u from the shoulder line at the body center (follows the chest)
        hip     u from the pelvis (follows the hips)
        floor   u from the feet at the body center (fixed to the world)
        sh_f    u from the far shoulder, world-aligned
  * 'ball' / 'anchor' take the same (space, x, y) form, plus
        hand_f / hand_n   u along / across that forearm, from the wrist
  * 'expr' is an EXPR name, '@face' (in-game default) or '@cheer' (celebration);
    'blink' closes the eyes of whatever face is showing; 'phase' animates FX marks
  * t in [0, 1): loops wrap. One-shot moves run 0 -> 1, and the game maps its
    own clock onto t (see MARKS), so keyframe times are part of the contract.
"""
import math

from .cast import BODY
from .geom import ap, unit
from .rig import arm_joints, solve

TAU = math.tau
LOOPS = {"idle", "run", "dribble", "hold", "celebrate"}

# The moment the game syncs to: jump_shot = ball at the set point (jump apex,
# release), dunk = ball through the rim. Everything before it is the wind-up.
MARKS = {"jump_shot": 0.75, "dunk": 0.6}

BR = BODY["ball_r"] * 60 / BODY["head_r"]   # ball radius in u
PALM = 0.85 * BR                             # wrist -> center of a ball resting on the palm


# ------------------------------------------------------------ keyframes
# What a key means when a keyframe leaves it out. Bone angles, '_air' and
# 'phase' default to 0; IK targets, flags and strings have no default.
_DEFAULT = {"_t": (0, 0), "hair": (6, 6, 8)}


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _blend(key, a, b, k):
    if a is None or b is None:
        present = a if b is None else b
        if key not in _DEFAULT and not _num(present):
            return a if k < 0.5 else b   # IK on/off, flags, strings: switch midway
        d = _DEFAULT.get(key, 0.0)
        a, b = (d, b) if a is None else (a, d)
    if _num(a) and _num(b):
        return a + (b - a) * k
    if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b):
        if all(_num(x) for x in a + b):
            return tuple(x + (y - x) * k for x, y in zip(a, b))
        if isinstance(a[0], str) and a[0] == b[0]:   # IK/ball spec in the same space
            return (a[0],) + tuple(x + (y - x) * k for x, y in zip(a[1:], b[1:]))
    return a if k < 0.5 else b


def keyed(t, keys):
    """Interpolate [(t, pose), ...] keyframes with smoothstep easing. Numbers
    and number tuples blend; anything else switches at the midpoint."""
    if t <= keys[0][0]:
        return dict(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            k = k * k * (3 - 2 * k)
            out = {key: _blend(key, a.get(key), b.get(key), k) for key in set(a) | set(b)}
            return {key: v for key, v in out.items() if v is not None}
    return dict(keys[-1][1])


def _sway(ph, base=(6, 6, 8), amp=(4, 3, 3)):
    """Idle hair sway: each chain link lags a little more than the last."""
    return tuple(b + a * math.sin(ph - 1.0 - 0.6 * i) for i, (b, a) in enumerate(zip(base, amp)))


def _bounce(b, hand_y):
    """Dribble geometry for bounce height b (1 = top, 0 = floor): the hand
    target rides the ball top; returns (hand y, ball center y) in floor space."""
    top, low = hand_y + 3 + BR, -(BR + 2)
    return hand_y + 10 * (1 - b), low + (top - low) * b ** 1.4


# -------------------------------------------------------- shared pieces
# Athletic ready stance (the in-game idle): knees bent, soles flat, hands up.
READY = {"_t": (0, 4), "chest": 6, "head": -3,
         "n_th": -24, "n_sh": 42, "n_ft": -18, "f_th": -6, "f_sh": 22, "f_ft": -16,
         "n_up": -18, "n_lo": -36, "f_up": -26, "f_lo": -28}

# Deep crouch used as the wind-up for every jump.
CROUCH = {"_t": (0, 6), "n_th": -26, "n_sh": 52, "n_ft": -26, "f_th": -20, "f_sh": 46, "f_ft": -26}


def signature_arms(p, variant, ph):
    """A girl's signature arm pose (showcase idle + in-game celebration)."""
    sw = math.sin(ph)
    if variant == "hip":   # hand planted on the hip, elbow out
        p["ik_n"] = ("hip", -26.7, -19, 1.0, 1.25)
    elif variant == "peace":   # V sign beside the cheek
        p["ik_n"] = ("head", -1.02, 0.62 + 0.03 * sw, -1.0, 1.4)
        p["hand_n"], p["arm_front"] = "peace", True
    elif variant == "wave":
        p["ik_f"] = ("head", 1.22, 0.22 + 0.08 * math.sin(2 * ph), 1.0, 1.45)
    elif variant == "cheer":   # both hands up
        p["ik_n"] = ("head", -1.16, 0.40 + 0.04 * sw, -1.0, 1.35)
        p["ik_f"] = ("head", 1.18, 0.34 - 0.04 * sw, 1.0, 1.4)
        p["arm_front"] = True
    elif variant == "fist":   # 'ganbare!' — fist pump + fist at the chest
        p["ik_f"] = ("head", 1.12, 0.12 + 0.05 * sw, 1.0, 1.45)
        p["ik_n"] = ("chest", -2, 20, 1.0, 1.2)
        p["hand_n"] = p["hand_f"] = "fist"
    elif variant == "point":   # 'you're next'
        p["ik_f"] = ("head", 1.40, 0.70 + 0.02 * sw, 1.0, 1.55)
        p["hand_f"] = "point"
    elif variant == "thumbs":
        p["ik_n"] = ("chest", 8, 16, 1.0, 1.2)
        p["hand_n"] = "thumb"
    return p


def _run_body(ph):
    """Run cycle legs/torso shared by run and dribble."""
    s1 = math.sin(ph)
    return {"_t": (0, -3 - 5 * abs(s1)), "root": 3, "chest": 9 + 1.5 * math.cos(2 * ph),
            "head": -8 - 1.5 * math.cos(2 * ph),
            "n_th": -34 * s1, "f_th": 34 * s1,
            "n_sh": 14 + 50 * max(0.0, math.cos(ph)), "f_sh": 14 + 50 * max(0.0, -math.cos(ph)),
            "n_ft": -10 * s1, "f_ft": 10 * s1, "n_up": 38 * s1, "n_lo": -55,
            "hair": (24 + 10 * math.sin(ph - 0.9), -6 + 8 * math.sin(ph - 1.6), -12 + 9 * math.sin(ph - 2.3)),
            "expr": "@face"}


# ------------------------------------------------------------ the moves
def idle(t, variant):
    """'ready' = the in-game athletic stance; anything else = showcase idle
    with the girl's signature arms."""
    ph = t * TAU
    sw = math.sin(ph)
    if variant == "ready":
        p = dict(READY, **{"_t": (0, 4 + 0.6 * sw), "chest": 6 + 1.0 * sw, "head": -3 + 1.5 * math.sin(ph - 0.6),
                           "n_up": -18 + 2 * sw, "f_up": -26 - 2 * sw, "hair": _sway(ph), "expr": "@face"})
    else:
        p = {"_t": (0, -0.8 * sw), "chest": -2 + 1.2 * sw, "head": 4 + 2.0 * math.sin(ph - 0.6),
             "n_up": 17 + 2 * sw, "n_lo": -12, "f_up": -13 - 2 * sw, "f_lo": 12,
             "n_th": -3, "n_sh": 3, "f_th": 4, "hair": _sway(ph)}
        signature_arms(p, variant, ph)
    if 0.62 <= t < 0.70:
        p["blink"] = True   # close the eyes, keep the rest of the face
    return p


def run(t, variant):
    ph = t * TAU
    p = _run_body(ph)
    p.update({"f_up": -38 * math.sin(ph), "f_lo": -55, "fx": "speed"})
    return p


def dribble(t, variant):
    """Running dribble, one bounce per step. 'still' = the showcase frame:
    hand meeting the ball at the top of the bounce, mid-stride."""
    ph = t * TAU
    p = _run_body(ph)
    if variant == "still":
        p.update({"n_th": -28, "n_sh": 30, "n_ft": -8, "f_th": 26, "f_sh": 52, "f_ft": 10,
                  "n_up": 30, "_t": (0, -6)})
        b = 1.0
    else:
        b = abs(math.cos(ph))
    hand, ball = _bounce(b, -84)
    p["ik_f"] = ("floor", 49, hand, 1.0, 1.25)
    p["ball"] = ("floor", 52, ball)
    p["fx"] = "speed"
    return p


def hold(t, variant):
    """Stationary dribble: ready stance, far hand pumping, near arm guarding."""
    ph = t * TAU
    b = abs(math.cos(ph))
    hand, ball = _bounce(b, -80)
    p = dict(READY, **{"_t": (0, 4 + 1.0 * (1 - b)), "chest": 7 + 1.0 * (1 - b), "head": -4,
                       "n_up": -32, "n_lo": -38, "hair": _sway(ph * 2, amp=(3, 2, 2)), "expr": "@face"})
    p["ik_f"] = ("floor", 44, hand, 1.0, 1.25)
    p["ball"] = ("floor", 47, ball)
    return p


def jump_shot(t, variant):
    """0 load -> 0.375 rise -> 0.75 set point (release at the apex) -> 1 follow-through."""
    tuck = {"n_th": -28, "n_sh": 50, "n_ft": -10, "f_th": 6, "f_sh": 34, "f_ft": 6}
    return keyed(t, [
        (0.0, dict(CROUCH, **{"chest": 8, "head": -4, "ik_f": ("chest", 24, 22, 1.0, 1.2),
                              "ik_n": ("chest", 14, 24, 1.0, 1.2), "ball": ("hand_f", PALM, 0),
                              "hair": (8, 6, 4), "expr": "focus"})),
        (0.375, {"chest": 0, "head": -8, "n_th": -12, "n_sh": 20, "n_ft": -8, "f_th": 2, "f_sh": 18,
                 "f_ft": -10, "ik_f": ("head", 1.00, 0.55, 1.0, 1.45), "ik_n": ("head", -1.10, 0.80, -1.0, 1.3),
                 "ball": ("hand_f", PALM, 0), "hair": (14, 8, 4), "_air": 30, "expr": "focus"}),
        (0.75, dict(tuck, **{"root": -3, "chest": -5, "head": -10,
                             "ik_f": ("head", 1.045, 0.4725, 1.0, 1.45), "ik_n": ("head", -1.18, 0.62, -1.0, 1.3),
                             "ball": ("hand_f", PALM, 0), "hair": (16, 10, 6), "_air": 46, "expr": "focus"})),
        (1.0, dict(tuck, **{"root": -3, "chest": -6, "head": -12,
                            "ik_f": ("head", 1.30, -0.05, 1.0, 1.6), "ik_n": ("head", -1.18, 0.62, -1.0, 1.3),
                            "hair": (16, 10, 6), "_air": 50, "expr": "focus"})),
    ])


def dunk(t, variant):
    """0 gather -> 0.2 rise -> 0.4 cock back -> 0.6 SLAM (ball at the rim) -> 0.8 fall -> 1 land."""
    tuck = {"n_th": -44, "n_sh": 72, "n_ft": -14, "f_th": 20, "f_sh": 64, "f_ft": 14}
    return keyed(t, [
        (0.0, dict(CROUCH, **{"chest": 12, "head": -4, "ik_f": ("chest", 30, 30, 1.0, 1.25),
                              "ik_n": ("chest", 34, 36, 1.0, 1.25), "ball": ("hand_f", PALM, 0),
                              "hair": (10, 6, 4), "expr": "shout"})),
        (0.2, {"chest": 6, "head": -6, "n_th": -36, "n_sh": 60, "n_ft": -12, "f_th": 14, "f_sh": 50,
               "f_ft": 8, "ik_f": ("chest", 34, -6, 1.0, 1.3), "ik_n": ("chest", 40, 2, 1.0, 1.3),
               "ball": ("hand_f", PALM, 0), "hair": (40, 10, 4), "_air": 40, "expr": "shout"}),
        # chibi arms can't lift the ball over the head, so she reaches up-forward
        (0.4, dict(tuck, **{"root": 4, "chest": 4, "head": -6, "n_up": -80, "n_lo": -20,
                            "ik_f": ("sh_f", 54, -54, 1.0, 1.5), "ball": ("hand_f", PALM, 0),
                            "hair": (60, 14, 8), "_air": 62, "expr": "shout"})),
        (0.6, dict(tuck, **{"root": 8, "chest": 14, "head": -8, "n_up": 64, "n_lo": -34,
                            "ik_f": ("sh_f", 50, 14, 1.0, 1.3), "ball": ("hand_f", 8, 22),
                            "fx": "burst", "anchor": ("hand_f", 8, 22), "hair": (78, 16, 10), "_air": 62,
                            "expr": "shout"})),
        (0.8, {"root": 2, "chest": 4, "head": -2, "n_th": -24, "n_sh": 34, "n_ft": -10, "f_th": 8,
               "f_sh": 30, "f_ft": 4, "n_up": -40, "n_lo": -30, "ik_f": ("head", 1.10, 0.10, 1.0, 1.4),
               "hair": (-20, -10, -6), "_air": 40, "expr": "fired_up"}),
        (1.0, dict(CROUCH, **{"_t": (0, 4), "chest": 8, "head": -2, "n_up": -20, "n_lo": -30, "f_up": -24,
                              "f_lo": -30, "hair": (10, 6, 6), "expr": "fired_up"})),
    ])


def block(t, variant):
    """0 crouch -> 1/3 rise -> 2/3 wall up (apex) -> 1 hold it."""
    return keyed(t, [
        (0.0, {"_t": (0, 5), "chest": 6, "head": -2, "n_th": -22, "n_sh": 44, "n_ft": -22, "f_th": -10,
               "f_sh": 30, "f_ft": -20, "n_up": -10, "n_lo": -20, "f_up": -14, "f_lo": -20,
               "hair": (8, 6, 4), "arm_front": True, "expr": "shout"}),
        (1 / 3, {"chest": 0, "head": -4, "n_th": -10, "n_sh": 26, "f_th": 6, "f_sh": 30,
                 "ik_n": ("head", -1.00, 0.90, -1.0, 1.3), "ik_f": ("head", 1.00, 0.95, 1.0, 1.3),
                 "hair": (10, 7, 5), "_air": 24, "arm_front": True, "expr": "shout"}),
        (2 / 3, {"chest": -4, "head": -4, "n_th": -10, "n_sh": 40, "f_th": 10, "f_sh": 46,
                 "ik_n": ("head", -1.14, 0.20, -1.0, 1.45), "ik_f": ("head", 1.16, 0.40, 1.0, 1.45),
                 "hair": (12, 8, 6), "_air": 40, "arm_front": True, "expr": "shout"}),
        (1.0, {"chest": -2, "head": -2, "n_th": -10, "n_sh": 40, "f_th": 10, "f_sh": 46,
               "ik_n": ("head", -1.12, 0.26, -1.0, 1.45), "ik_f": ("head", 1.14, 0.46, 1.0, 1.45),
               "hair": (-6, 0, 6), "_air": 30, "arm_front": True, "expr": "shout"}),
    ])


def steal(t, variant):
    """0 wind-up -> 1/3 swipe -> 2/3 follow-through -> 1 recover."""
    lunge = {"_t": (0, 5), "root": 12, "chest": 14, "head": -12, "n_th": -50, "n_sh": 56, "n_ft": -6,
             "f_th": 36, "f_sh": 14, "f_ft": 16, "f_up": 44, "f_lo": -30, "expr": "smug"}
    return keyed(t, [
        (0.0, {"_t": (0, 2), "root": -4, "chest": -4, "head": 0, "n_th": -16, "n_sh": 24, "n_ft": -8,
               "f_th": 12, "f_sh": 18, "f_ft": -30, "n_up": 34, "n_lo": -40, "f_up": 20, "f_lo": -20,
               "hair": (20, 4, 0), "expr": "smug"}),
        (1 / 3, dict(lunge, **{"ik_n": ("floor", 82, -74, 1.0, 1.5), "fx": "swoosh",
                               "anchor": ("floor", 82, -74), "hair": (40, 4, -8)})),
        (2 / 3, dict(lunge, **{"root": 14, "chest": 16, "ik_n": ("floor", 74, -44, 1.0, 1.5),
                               "hair": (44, 6, -6)})),
        (1.0, {"_t": (0, 3), "root": 6, "chest": 6, "head": -6, "n_th": -32, "n_sh": 40, "n_ft": -8,
               "f_th": 22, "f_sh": 20, "f_ft": -30, "f_up": 24, "f_lo": -24,
               "ik_n": ("floor", 52, -62, 1.0, 1.4), "hair": (24, 4, 0), "expr": "smug"}),
    ])


def hurt(t, variant):
    """0 hit -> 1/3 falling -> 2/3 plop -> 1 seeing stars."""
    sit = {"_t": (0, 54), "root": -12, "chest": -6, "head": 10, "n_th": -76, "n_sh": 14, "n_ft": -30,
           "f_th": -66, "f_sh": 26, "f_ft": -24, "ik_n": ("floor", -40, -6, 1.0, 1.4),
           "ik_f": ("floor", -6, -4, 1.0, 1.4), "hair": (-10, 4, 8), "expr": "dizzy"}
    return keyed(t, [
        (0.0, {"root": -10, "chest": -10, "head": 14, "n_th": -8, "n_sh": 10, "f_th": 10, "f_sh": 16,
               "n_up": 150, "n_lo": 10, "f_up": 140, "f_lo": 20, "hair": (-20, 0, 4), "expr": "effort"}),
        (1 / 3, {"_t": (0, 26), "root": -26, "chest": -10, "head": 10, "n_th": -60, "n_sh": 24,
                 "f_th": -46, "f_sh": 30, "n_up": 110, "f_up": 100, "hair": (-14, 2, 6),
                 "expr": "effort"}),
        (2 / 3, dict(sit, phase=0.0)),
        (1.0, dict(sit, head=14, chest=-4, phase=0.5)),
    ])


def celebrate(t, variant):
    """Hop loop with the girl's signature arms (in-sprite hop: the game
    doesn't lift celebrating sprites)."""
    ph = t * TAU
    hop = abs(math.sin(math.pi * t))
    p = {"_t": (0, -20 * hop), "_air": 6 * hop, "chest": -3, "head": 8 + 3 * math.sin(ph),
         "n_th": -8, "n_sh": 6 + 20 * hop, "f_th": 20, "f_sh": 66, "f_ft": 12,
         "hair": (-4 + 12 * math.cos(ph), -2 + 6 * math.cos(ph - 0.7), 2 + 4 * math.cos(ph - 1.4)),
         "expr": "@cheer"}
    return signature_arms(p, variant or "cheer", ph)


def on_fire(t, variant):
    """Showcase only: in the game the fire is an aura sprite behind any move."""
    return {"_t": (0, 4), "chest": 4, "head": -4, "n_th": -16, "n_sh": 22, "n_ft": -6, "f_th": 14,
            "f_sh": 18, "f_ft": 6, "hair": (38, 10, -6), "ik_f": ("head", 1.12, 0.36, 1.0, 1.4),
            "ik_n": ("chest", 8, 22, 1.0, 1.2), "fx": "fire", "expr": "fired_up"}


MOVES = {"idle": idle, "run": run, "dribble": dribble, "hold": hold, "jump_shot": jump_shot, "dunk": dunk,
         "block": block, "steal": steal, "hurt": hurt, "celebrate": celebrate, "on_fire": on_fire}


# ------------------------------------------------------- world resolve
def _point(spec, pose, J, bones, P, g):
    space, x, y = spec[0], spec[1], spec[2]
    u, R = g["R"] / 60, g["R"]
    if space == "floor":
        return (g["cx"] + x * u, g["floor"] + y * u)
    M = solve(bones, pose)
    if space == "head":
        return ap(M["head"], (g["hx"] + x * R, g["hy"] + y * R))
    if space == "chest":
        return ap(M["chest"], (g["cx"] + x * u, g["sh_y"] + y * u))
    if space == "hip":
        return ap(M["root"], (g["cx"] + x * u, g["hip_y"] + y * u))
    if space == "sh_f":
        s = ap(M["chest"], J["sh_f"])
        return (s[0] + x * u, s[1] + y * u)
    if space in ("hand_f", "hand_n"):
        _, E, W = arm_joints(M, J, P, pose, space[-1])
        d = unit((W[0] - E[0], W[1] - E[1]))
        return (W[0] + (d[0] * x - d[1] * y) * u, W[1] + (d[1] * x + d[0] * y) * u)
    raise ValueError("unknown space %r" % space)


def make_pose(name, J, bones, P, g, t=0.0, variant=None, lift=True):
    """Build a move at time t and resolve it to world space.
    Returns (pose, ball_center | None, expr | None, fx_kind | None, fx_anchor | None)."""
    t = t % 1.0 if name in LOOPS else min(max(t, 0.0), 1.0)
    p = MOVES[name](t, variant)
    u = g["R"] / 60
    tx, ty = p.pop("_t", (0, 0))
    air = p.pop("_air", 0.0)
    p["_t"] = (tx * u, (ty - (air if lift else 0.0)) * u)
    for side in ("n", "f"):
        spec = p.pop("ik_" + side, None)
        if spec:
            p["ik_" + side] = (_point(spec, p, J, bones, P, g), spec[3], spec[4])
    ball, anchor = p.pop("ball", None), p.pop("anchor", None)
    ball = _point(ball, p, J, bones, P, g) if ball else None
    anchor = _point(anchor, p, J, bones, P, g) if anchor else None
    return p, ball, p.pop("expr", None), p.pop("fx", None), anchor
