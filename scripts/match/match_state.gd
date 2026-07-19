class_name MatchState
extends RefCounted
## Pure match bookkeeping: score, clock, quarters, possession, fire streaks,
## per-player points. No nodes, no rendering — this is the part of the game
## state that the post-v1 netcode will replicate.

enum Phase { PLAY, QUARTER_BREAK, OVERTIME, ENDED }

var settings: MatchSettings
var ballers: Array = []  # set by MatchScene after build
var scores := [0, 0]
var quarter := 1
var clock := 0.0
var shot_clock := 0.0
var phase: int = Phase.PLAY
var possession := 0
var player_points := {}  # Baller -> int
var streaks := {}  # PER_PLAYER: Baller -> makes; PER_TEAM: team int -> makes
var fire_baskets := {}  # Baller -> makes while on fire (burnout counter)


func _init(s: MatchSettings) -> void:
	settings = s
	clock = s.quarter_length_sec
	shot_clock = s.shot_clock_sec


func register_basket(team: int, points: int, scorer) -> Dictionary:
	## Returns fire transitions for MatchScene to apply:
	## {ignite: [Baller], douse: [Baller], heating: [Baller]}
	scores[team] += points
	player_points[scorer] = int(player_points.get(scorer, 0)) + points
	var ev := {"ignite": [], "douse": [], "heating": []}
	if settings.fire_mode == MatchSettings.FireMode.PER_PLAYER:
		_fire_per_player(team, scorer, ev)
	else:
		_fire_per_team(team, ev)
	return ev


func _fire_per_player(team: int, scorer, ev: Dictionary) -> void:
	# NBA Jam rules: 3 consecutive personal buckets ignites; an opponent
	# basket douses; burning out after N buckets on fire douses too.
	for b in ballers:
		if b.team != team and b.on_fire:
			ev.douse.append(b)
			streaks[b] = 0
		if b != scorer:
			streaks[b] = 0
	var s: int = int(streaks.get(scorer, 0)) + 1
	streaks[scorer] = s
	if scorer.on_fire:
		var fb: int = int(fire_baskets.get(scorer, 0)) + 1
		fire_baskets[scorer] = fb
		if fb >= settings.fire_baskets_before_burnout:
			ev.douse.append(scorer)
			streaks[scorer] = 0
	elif s >= settings.fire_streak_to_ignite:
		ev.ignite.append(scorer)
		fire_baskets[scorer] = 0
	elif s == settings.fire_streak_to_ignite - 1:
		ev.heating.append(scorer)


func _fire_per_team(team: int, ev: Dictionary) -> void:
	# Variant mode: unanswered TEAM scores light up the whole squad.
	streaks[team] = int(streaks.get(team, 0)) + 1
	streaks[1 - team] = 0
	for b in ballers:
		if b.team != team and b.on_fire:
			ev.douse.append(b)
	if int(streaks.get(team, 0)) == settings.fire_streak_to_ignite:
		for b in ballers:
			if b.team == team and not b.on_fire:
				ev.ignite.append(b)


func leader() -> int:
	return 0 if scores[0] >= scores[1] else 1


func mvp():
	var best = null
	var best_pts := -1
	for b in player_points:
		if int(player_points[b]) > best_pts:
			best_pts = int(player_points[b])
			best = b
	return best
