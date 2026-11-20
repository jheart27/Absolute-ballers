"""Chibi rig — the Absolute Ballers character art pipeline.

A 2D cutout rig (the Spine / gacha battle-sprite technique) authored and posed
entirely in code. Characters, poses and expressions are all data, so the whole
cast shares one rig. Run from the repo root:

    python3 -m tools.chibi_rig showcase docs/art     # preview sheets + GIF
    python3 -m tools.chibi_rig one aki dribble joy out.png
    python3 -m tools.chibi_rig bake                   # game sprite sheets

Module map (each module only imports from the ones above it):

    geom     2D math: bone transforms, curves, shape builders
    paint    supersampled Canvas, colors, gradients, outlines
    cast     the girls (CAST), palettes, body proportions (BODY)
    rig      skeleton, forward kinematics, stretchy arm IK
    body     arms/hands, legs/sneakers, shorts, jersey, neck
    face     eyes, mouths, brows, FX marks, expressions (EXPR)
    hair     bangs, back hair, tails, buns, shine, ahoge
    props    accessories, the ball, effect layers
    poses    every move as bone angles + IK targets
    render   draws one character in order -> RGBA image
    sheets   showcase sheets for docs/art
    bake     sprite sheets for the game (the BallerAnim contract)
"""
