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
var player_stats := {}  # Baller -> {pts, dunks, threes, steals, blocks}
var streaks := {}  # PER_PLAYER: Baller -> makes; PER_TEAM: team int -> makes
var fire_baskets := {}  # Baller -> makes while on fire (burnout counter)


func _init(s: MatchSettings) -> void:
	settings = s
	clock = s.quarter_length_sec
	shot_clock = s.shot_clock_sec


func stats_for(baller) -> Dictionary:
	if not player_stats.has(baller):
		player_stats[baller] = {
			"pts": 0, "dunks": 0, "threes": 0, "steals": 0, "blocks": 0}
	return player_stats[baller]


func add_steal(baller) -> void:
	stats_for(baller).steals += 1


func add_block(baller) -> void:
	stats_for(baller).blocks += 1


func register_basket(team: int, points: int, scorer, was_dunk: bool) -> Dictionary:
	## Returns fire transitions for MatchScene to apply:
	## {ignite: [Baller], douse: [Baller], heating: [Baller]}
	scores[team] += points
	var stat := stats_for(scorer)
	stat.pts += points
	if was_dunk:
		stat.dunks += 1
	if points == 3:
		stat.threes += 1
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
	## Points-weighted, but hustle counts: steals/blocks are worth 2, dunks 1.
	var best = null
	var best_score := -1.0
	for b in player_stats:
		var s: Dictionary = player_stats[b]
		var score: float = s.pts + 2.0 * (s.steals + s.blocks) + s.dunks
		if score > best_score:
			best_score = score
			best = b
	return best
