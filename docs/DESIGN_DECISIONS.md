# Design decisions (v1 defaults)

The brief left four questions open. These are the shipped defaults — every
one of them is a data setting, not a code path, so changing your mind is a
menu toggle or a one-line edit in `MatchSettings`.

## 1. Team size — **3v3 default, fully configurable**

The brief said 3v3 in MATCH FORMAT and 5v5 in CORE MECHANICS, plus "might
want 5v5 later and/or 1v1". Resolution: `MatchSettings.team_size` drives
everything (spawns, AI spacing slots, lobby caps). The main menu exposes
1v1 / 2v2 / 3v3 / 5v5. 3v3 is the default because it keeps the camera
readable and the AI legible; 5v5 already works, it's just denser.

## 2. Controls — **NBA Jam classic (context-sensitive)**

A = shoot/block, B = pass/steal, X/RT = turbo, Y = switch. Chosen over
dedicated per-action buttons for authenticity and couch accessibility.
Mapping lives in `InputSetup` (keyboard) and `HumanInput` (pads) — one file
each to change.

## 3. Match format — **4 quarters x 2:00, sudden-death OT**

`quarter_count`, `quarter_length_sec` in MatchSettings; menu exposes 1:00 /
2:00 / 3:00 quarters. Overtime is untimed next-bucket-wins (arcade-fast,
tournament-friendly). A first-to-X streetball mode would slot into
`MatchScene._tick_clock` if ever wanted.

## 4. On fire — **per player, with per-team variant included**

Classic rules: 3 consecutive personal buckets ignites (opponent basket or
any other scorer resets the count); fire ends when the opponent scores or
after 4 baskets on fire. Boosts: +speed, +22% shot chance, +90px dunk
range, unlimited turbo, aura overlay.
`MatchSettings.fire_mode = PER_TEAM` switches to whole-squad ignition after
3 unanswered team scores (menu toggle: ON FIRE: PER PLAYER / PER TEAM).
Logic lives entirely in `MatchState._fire_per_player/_fire_per_team`.

## Camera (called out as a core problem in the brief)

`MatchCamera` fits all ballers + ball with padding, weights the center 45%
toward the ball, and clamps zoom to `MIN_ZOOM = 0.63` — the readability
floor at which a 64px sprite still renders ~40px on a 720p viewport. The
court art is deliberately oversized (2048x1280 with arena/crowd painted
outside the apron) so max zoom-out shows arena, never void. If sprites feel
small at 5v5, raise MIN_ZOOM — the camera will pan more instead.
