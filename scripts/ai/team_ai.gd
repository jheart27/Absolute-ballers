class_name TeamAI
extends RefCounted
## Per-team coordinator: defensive matchup assignment, offensive spacing
## slots, loose-ball chaser election, and the difficulty knobs that
## individual AIInput brains read. One instance per team, updated by
## MatchScene before the ballers sim.

# Spacing slots in attack-half coords (attacking the +x hoop); mirrored for
# the other side. Order matters: first team_size-1 slots get used.
const SLOTS: Array = [
	Vector2(480.0, -170.0),
	Vector2(480.0, 170.0),
	Vector2(300.0, 0.0),
	Vector2(690.0, -205.0),
	Vector2(690.0, 205.0),
]

const DIFF_PARAMS: Array = [
	{  # 0 rookie
		"think_interval": 0.55, "release_window": 0.45, "open_shot_dist": 130.0,
		"shoot_urge": 0.5, "pass_threshold": 90.0, "steal_rate": 0.35,
		"block_urge": 0.35, "shove_chance": 0.15,
	},
	{  # 1 arcade
		"think_interval": 0.38, "release_window": 0.25, "open_shot_dist": 105.0,
		"shoot_urge": 0.7, "pass_threshold": 70.0, "steal_rate": 0.7,
		"block_urge": 0.6, "shove_chance": 0.3,
	},
	{  # 2 legend
		"think_interval": 0.24, "release_window": 0.12, "open_shot_dist": 85.0,
		"shoot_urge": 0.85, "pass_threshold": 55.0, "steal_rate": 1.2,
		"block_urge": 0.85, "shove_chance": 0.45,
	},
]

var team := 0
var difficulty := 1
var match_scene = null

var _marks := {}  # defender Baller -> attacker Baller
var _retarget_t := 0.0


func _init(team_idx: int, diff: int, match_ref) -> void:
	team = team_idx
	difficulty = diff
	match_scene = match_ref


func diff_params() -> Dictionary:
	return DIFF_PARAMS[clampi(difficulty, 0, 2)]


func update(delta: float) -> void:
	_retarget_t -= delta
	if _retarget_t <= 0.0:
		_retarget_t = 0.4
		_assign_marks()


func _assign_marks() -> void:
	_marks.clear()
	var ball = match_scene.ball
	var opp_sorted: Array = match_scene.opponents_of(team).duplicate()
	# cover the ball handler first, then sweep the rest
	opp_sorted.sort_custom(func(a, b):
		if ball.holder == a:
			return true
		if ball.holder == b:
			return false
		return a.position.x < b.position.x)
	var free: Array = match_scene.teammates_of(team).duplicate()
	for opp in opp_sorted:
		if free.is_empty():
			break
		var best = null
		var best_d := INF
		for d in free:
			var dd: float = d.position.distance_to(opp.position)
			if dd < best_d:
				best_d = dd
				best = d
		_marks[best] = opp
		free.erase(best)


func defensive_mark(baller):
	return _marks.get(baller, match_scene.ball.holder)


func offense_slot(baller) -> Vector2:
	var ball_holder = match_scene.ball.holder
	var slot_i := 0
	for tm in match_scene.teammates_of(team):
		if tm == ball_holder:
			continue
		if tm == baller:
			break
		slot_i += 1
	var s: Vector2 = SLOTS[slot_i % SLOTS.size()]
	if CourtGeometry.hoop_pos(team).x < 0.0:
		s.x = -s.x
	return s


func should_chase(baller) -> bool:
	## Nearest 1-2 teammates go for a loose ball; the rest hold shape.
	var mates: Array = match_scene.teammates_of(team).duplicate()
	var ballp: Vector2 = match_scene.ball.position
	mates.sort_custom(func(a, b):
		return a.position.distance_to(ballp) < b.position.distance_to(ballp))
	var chasers := 1 if mates.size() <= 2 else 2
	return mates.slice(0, chasers).has(baller)
