extends Node
## Global signal hub (autoload "EventBus").
## The simulation emits facts; UI, announcer, and Steam layers listen.
## Keeping the sim unaware of presentation is a prerequisite for the
## post-v1 online-multiplayer split (see docs/ONLINE_MULTIPLAYER.md).
##
## These signals are emitted from OTHER classes (EventBus.x.emit(...)), which
## the per-class analyzer can't see, so it flags every one as "unused" — a
## known false positive for an autoload signal bus. Suppress it class-wide so
## real warnings stay visible in the debugger.
@warning_ignore_start("unused_signal")

signal announce(text: String, tier: int)  # tier 0 = small .. 2 = huge
signal basket_scored(team: int, points: int, scorer, was_dunk: bool)
signal score_changed(scores: Array)
signal fire_changed(baller, on_fire: bool)
signal shot_taken(shooter)
signal shot_blocked(blocker, shooter)
signal steal_made(stealer, victim)
signal knockdown(victim)
signal quarter_started(quarter: int)
signal overtime_started
signal match_ended(winner_team: int, winner_has_human: bool)
signal tournament_won
