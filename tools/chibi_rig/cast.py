"""The cast: skin tones, palettes derived from a few base colors, the CAST
table (one entry per girl), and the shared chibi body proportions."""


from .paint import hsv, mix


SKINS = {
    "fair": dict(skin=(255, 231, 216), skin_top=(255, 241, 232), skin_sh=(245, 188, 178),
                 skin_sh2=(226, 150, 150), skin_ln=(150, 84, 92), blush=(255, 124, 146)),
    "tan": dict(skin=(242, 200, 164), skin_top=(249, 216, 186), skin_sh=(216, 154, 126),
                skin_sh2=(190, 122, 104), skin_ln=(122, 68, 56), blush=(242, 110, 112)),
    "deep": dict(skin=(198, 142, 106), skin_top=(212, 160, 124), skin_sh=(166, 110, 82),
                 skin_sh2=(142, 90, 68), skin_ln=(86, 46, 34), blush=(216, 98, 98)),
}


COMMON = dict(
    white=(255, 255, 255), eye_sh=(210, 212, 242), lash=(44, 18, 34),
    mouth=(152, 38, 62), tongue=(248, 130, 146), teeth=(255, 255, 255),
    sock=(250, 250, 253), sock_sh=(206, 212, 230), sock_ln=(102, 108, 140),
    shoe=(250, 250, 253), shoe_sh=(200, 208, 228), sole=(66, 62, 88),
    ball=(244, 128, 46), ball_top=(252, 162, 86), ball_sh=(192, 78, 26), ball_ln=(98, 36, 12),
    tear=(178, 220, 255), tear_ln=(92, 146, 214), spark=(255, 240, 140), spark_ln=(232, 168, 40),
    anger=(234, 52, 76), gold=(255, 212, 92), gold_sh=(214, 150, 48), gold_ln=(118, 72, 20),
    frame=(64, 52, 78), lens=(200, 228, 255), bandage=(244, 206, 168), bandage_ln=(170, 120, 90),
)

# Everything drawn in these kit colors is the team uniform. The game bake
# renders it in grayscale and tints it per team at runtime (see bake.py).
KIT_KEYS = ("jersey", "jersey_top", "jersey_sh", "jersey_ln", "shorts", "shorts_sh")
# Neutral grays: the game multiplies these by the team color, so the jersey
# body (234) comes out at about the team color itself.
KIT_GRAY = dict(jersey=(234, 234, 234), jersey_top=(252, 252, 252), jersey_sh=(168, 168, 168),
                jersey_ln=(70, 70, 70), shorts=(216, 216, 216), shorts_sh=(152, 152, 152))


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


# One entry per girl. Fields:
#   hair / eyes / kit   base colors (kit = showcase uniform; in-game it's the team's)
#   skin                fair | tan | deep
#   style               ponytail | twintails | bob | long | buns | short
#   bangs               default | blunt | swept | spiky
#   acc                 scrunchie | ribbons | clip | flower | headband | glasses | bow | bandaid | moon
#   tilt                eye shape: + sharp (tsurime), - gentle (tareme)
#   idle                signature pose (showcase + celebration): wave | peace | hip | cheer | fist | point | thumbs
#   signature           showcase expression;  face = in-game default;  cheer = celebration face
CAST = {
    "aki": dict(name="AKI", tag="Captain of chaos", hair=(232, 62, 78), eyes=(220, 54, 76),
                kit=(64, 198, 236), skin="fair", style="ponytail", acc="scrunchie", bangs="default",
                tilt=0.15, number="7", ahoge=True, idle="wave", signature="smile"),
    "yumi": dict(name="YUMI", tag="Splash queen", hair=(88, 130, 242), eyes=(64, 116, 232),
                 kit=(255, 120, 170), skin="fair", style="twintails", acc="ribbons", bangs="default",
                 tilt=-0.45, number="3", ahoge=True, idle="peace", signature="wink", cheer="wink"),
    "rin": dict(name="RIN", tag="Blink and she's gone", hair=(62, 56, 90), hair_hi=(160, 168, 224),
                eyes=(168, 102, 234), kit=(46, 44, 60), trim=(255, 208, 90), skin="fair", style="bob",
                acc="clip", bangs="blunt", tilt=0.75, number="11", ahoge=False, idle="hip",
                signature="smug", face="smug", cheer="smug"),
    "hana": dict(name="HANA", tag="Small package, big slam", hair=(250, 154, 194), eyes=(62, 182, 134),
                 kit=(98, 214, 172), skin="fair", style="long", acc="flower", bangs="swept",
                 tilt=-0.2, number="23", ahoge=False, idle="cheer", signature="joy"),
    "miko": dict(name="MIKO", tag="Hands of a fox", hair=(250, 210, 100), eyes=(232, 128, 40),
                 kit=(68, 102, 216), skin="tan", style="buns", acc="headband", bangs="spiky",
                 tilt=0.35, number="5", ahoge=True, idle="fist", signature="fired_up", cheer="fired_up"),
    "sora": dict(name="SORA", tag="The wall", hair=(64, 192, 188), eyes=(40, 146, 204),
                 kit=(255, 160, 64), skin="fair", style="bob", acc="glasses", bangs="default",
                 tilt=0.25, number="8", ahoge=False, idle="point", signature="focus", face="focus"),
    "kaede": dict(name="KAEDE", tag="Paint bully", hair=(150, 84, 204), eyes=(222, 62, 122),
                  kit=(232, 64, 80), skin="fair", style="long", acc="bow", bangs="blunt",
                  tilt=0.55, number="13", ahoge=False, idle="hip", signature="cool", face="cool",
                  cheer="cool"),
    "nao": dict(name="NAO", tag="Tempo setter", hair=(240, 132, 60), eyes=(198, 108, 40),
                kit=(126, 204, 84), skin="tan", style="short", acc="bandaid", bangs="spiky",
                tilt=0.2, number="2", ahoge=True, idle="thumbs", signature="cheeky", face="cheeky"),
    "tsuki": dict(name="TSUKI", tag="Cold-blooded closer", hair=(206, 212, 230), hair_hi=(255, 255, 255),
                  eyes=(116, 136, 230), kit=(62, 72, 134), skin="fair", style="long", acc="moon",
                  bangs="swept", tilt=0.6, number="9", ahoge=False, idle="wave", signature="cool",
                  face="cool", cheer="cool"),
    "rei": dict(name="REI", tag="Full-court menace", hair=(84, 184, 96), eyes=(250, 190, 60),
                kit=(250, 226, 90), skin="deep", style="twintails", acc="ribbons", bangs="spiky",
                tilt=0.45, number="1", ahoge=True, idle="fist", signature="shout", face="cheeky",
                cheer="shout"),
}


def palette(cid, kit=None):
    """kit=None: the girl's showcase uniform. kit='gray' | 'black' | 'white':
    a neutral team uniform (white trim) for baking game sprites."""
    ch = CAST[cid]
    pal = dict(COMMON)
    pal.update(SKINS[ch["skin"]])
    pal.update(hair_pal(ch["hair"], ch.get("hair_hi")))
    pal.update(eye_pal(ch["eyes"]))
    if kit is None:
        pal.update(kit_pal(ch["kit"], ch.get("trim", (255, 255, 255))))
    else:
        pal.update(kit_pal((128, 128, 128)))
        fixed = {"gray": None, "black": (0, 0, 0), "white": (255, 255, 255)}[kit]
        for k in KIT_KEYS:
            pal[k] = KIT_GRAY[k] if fixed is None else fixed
    return pal


BODY = dict(cx=180, floor=432, foot_h=10, shin=34, thigh=32, torso_low=26, torso_up=32,
            neck=5, head_r=60, shoulder_w=46, chest_w=44, waist_w=36, hip_w=46,
            upper_arm=27, fore_arm=24, hand_r=7.6, ball_r=19,
            w_up=(16, 13.5), w_lo=(13.5, 12), w_th=(24, 18), w_sh=(19, 12.5), lw=2.4, stroke=1.8)


def body_params(s=1.0, cx=None, floor=None):
    b = {k: (tuple(x * s for x in v) if isinstance(v, tuple) else v * s) for k, v in BODY.items()}
    if cx is not None:
        b["cx"] = cx
    if floor is not None:
        b["floor"] = floor
    return b
