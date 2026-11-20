"""Body parts: arms (with hand shapes), legs + sneakers, midriff + shorts,
jersey, neck."""

import math

from .geom import ap, apl, capsule, catmull, ell, mrot, qbez, rell, unit
from .paint import C, Grad, dim


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
    elif hand == "point":   # index finger out along the forearm
        polys += [rell(hc[0], hc[1], hr * 0.95, hr * 1.0, ang, 24), thumb]
        base = (hc[0] + d[0] * hr * 0.50, hc[1] + d[1] * hr * 0.50)
        polys.append(capsule(base, hr * 0.48, (base[0] + d[0] * hr * 1.55, base[1] + d[1] * hr * 1.55), hr * 0.40))
    elif hand == "thumb":   # thumbs-up: fist with the thumb pointing straight up
        polys += [rell(hc[0], hc[1], hr * 1.04, hr * 1.04, ang, 24)]
        base = (hc[0], hc[1] - hr * 0.55)
        polys.append(capsule(base, hr * 0.52, (base[0] + hr * 0.10, base[1] - hr * 1.25), hr * 0.44))
    elif hand == "fist":
        polys += [rell(hc[0], hc[1], hr * 1.04, hr * 1.04, ang, 24)]
    else:
        polys += [rell(hc[0], hc[1], hr * 0.98, hr * 1.16, ang, 28), thumb]
    cv.union(polys, sk, sks, ln, P["lw"], shift=P["w_up"][0] * 0.34)
    if hand in ("fist", "thumb"):   # knuckle creases
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
