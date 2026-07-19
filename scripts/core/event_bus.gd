extends Node
## Global signal hub (autoload "EventBus").
## The simulation emits facts; UI, announcer, and Steam layers listen.
## Keeping the sim unaware of presentation is a prerequisite for the
## post-v1 online-multiplayer split (see docs/ONLINE_MULTIPLAYER.md).

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
