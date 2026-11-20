"""Command line: python3 -m tools.chibi_rig {showcase,one,bake} ..."""

import os
import sys

from .render import render
from .sheets import (
    anim_gif,
    court_bg,
    sheet_actions,
    sheet_expressions,
    sheet_portraits,
    sheet_roster,
)


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
    if argv and argv[0] == "bake":
        from .bake import bake, preview   # numpy is only needed for the bake
        for p in bake(argv[1:] or None):
            print("wrote", os.path.relpath(p))
        print("wrote", preview(os.path.join("docs", "art", "game_sprites.png")))
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
