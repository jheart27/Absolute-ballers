"""The skeleton: joints from body proportions, forward kinematics, and
stretchy 2-bone IK for arms."""

import math

from .geom import T, about, ap, mm


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
