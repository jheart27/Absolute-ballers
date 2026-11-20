"""render(): assembles one character in draw order (back hair -> far limbs
-> body -> face -> front hair -> FX marks) and composites FX + shadow."""


from PIL import Image, ImageDraw, ImageFilter

from .geom import apl, ell
from .paint import C, Canvas, Grad, OUTLINE, dim
from .cast import BODY, CAST, body_params, palette
from .rig import arm_joints, build, solve
from .body import draw_arm, draw_jersey, draw_leg, draw_lower_body, draw_neck
from .face import EXPR, draw_brows, draw_extras, draw_eye, draw_mouth, face_outline
from .hair import (
    bangs_poly,
    bob_poly,
    cap_poly,
    draw_buns,
    draw_front_hair,
    draw_long_back,
    draw_tails,
)
from .props import draw_accessory, draw_ball, fx_layer
from .poses import make_pose


def face_for(ch, name):
    """Resolve '@face' (in-game default) and '@cheer' (celebration) per girl."""
    if name == "@face":
        return ch.get("face", "smile")
    if name == "@cheer":
        return ch.get("cheer", "joy")
    return name


def render(cid, pose_name="idle", expr_name=None, t=0.0, scale=1.0, w=360, h=480, cx=None,
           floor=None, fx=True, shadow=True, variant=None, ball=True, lift=True, kit=None, info=None,
           resample=Image.LANCZOS):
    """One character as an RGBA image.
      variant   move variant (default: the girl's signature pose)
      ball      draw the ball if the move has one (the game draws its own)
      lift      include jump height; game sprites leave it out (the engine lifts them)
      kit       None = showcase uniform, 'gray' | 'black' | 'white' = team-kit bake passes
      info      optional dict, filled with the ball center (or None) for the bake
      resample  final downsample filter (the bake uses BOX, see Canvas.finish)"""
    ch = CAST[cid]
    pal = palette(cid, kit)
    P = body_params(scale, cx=cx if cx is not None else BODY["cx"] * scale,
                    floor=floor if floor is not None else BODY["floor"] * scale)
    J, bones, g = build(P)
    pose, ball_c, pose_expr, fx_kind, anchor = make_pose(
        pose_name, J, bones, P, g, t, variant or ch.get("idle"), lift)
    if info is not None:
        info["ball"] = ball_c
    ex = EXPR[face_for(ch, expr_name or pose_expr or ch["signature"])]
    if pose.get("blink"):
        ex = dict(ex, eyes="blink")
    phase = pose.get("phase", t)
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
    draw_accessory(cv, Mh, g, pal, P, ch, roots, "back")
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
    draw_extras(cv, Mh, ex.get("extras", []), pal, g, lw, "face", phase)
    draw_accessory(cv, Mh, g, pal, P, ch, roots, "face")

    # ---- front hair, accessories, brows, FX marks
    draw_front_hair(cv, Mh, g, pal, P, ch)
    draw_accessory(cv, Mh, g, pal, P, ch, roots, "top")
    draw_brows(cv, Mh, ex["brows"], pal, g)
    draw_extras(cv, Mh, ex.get("extras", []), pal, g, lw, "top", phase)
    if pose.get("arm_front"):
        draw_arm(cv, arms["n"], P, pal, far=False, band=True, hand=pose.get("hand_n", "mitten"))
    if ball and ball_c is not None:
        draw_ball(cv, ball_c, P["ball_r"], pal, lw * 0.9)
    cv.outline_pass(OUTLINE, P["stroke"])
    char = cv.finish(resample)

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
