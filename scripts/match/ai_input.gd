class_name AIInput
extends RefCounted
## The per-baller AI brain. Produces the exact same PlayerIntent a human
## would, so AI and humans are interchangeable pawn-by-pawn (this is also
## what makes "switch player" trivial: swap the controller reference).
## Strategy comes from TeamAI (marks, slots, difficulty params); this class
## turns it into moment-to-moment intents.

var baller = null
var team_ai: TeamAI = null

var _think_t := 0.0
var _cut_timer := 0.0
var _cutting_t := 0.0
var _strafe := 0.0
var _strafe_t := 0.0


func _init(b, t_ai: TeamAI) -> void:
	baller = b
	team_ai = t_ai


func poll(delta: float) -> PlayerIntent:
	var it := PlayerIntent.new()
	var b = baller
	var ms = b.match_scene
	var diff := team_ai.diff_params()
	_think_t -= delta
	_strafe_t -= delta

	# mid-air with the ball: time the release near the apex (with difficulty error)
	if b.state == Baller.State.JUMP and b.charging_shot:
		if b.zvel <= Baller.JUMP_IMPULSE * float(diff.release_window):
			it.shoot_released = true
		return it
	if b.state != Baller.State.IDLE and b.state != Baller.State.RUN:
		return it

	var ball = ms.ball
	if ball.holder == b:
		_offense_with_ball(it, diff, ms)
	elif ball.holder != null and ball.holder.team == b.team:
		_offense_off_ball(it, delta, ms)
	elif ball.holder != null:
		_defense(it, diff, delta, ms)
	else:
		_loose_ball(it, ms)
	return it


func _offense_with_ball(it: PlayerIntent, diff: Dictionary, ms) -> void:
	var b = baller
	var hoop := CourtGeometry.hoop_pos(b.team)
	var dist: float = b.position.distance_to(hoop)
	var openness: float = ms.nearest_opponent_distance(b)

	it.move = b.position.direction_to(hoop)
	if _strafe_t > 0.0:
		it.move = (it.move + Vector2(0.0, _strafe)).normalized()
	it.turbo = dist > 500.0 and b.turbo_meter > 25.0

	if _think_t > 0.0:
		return
	_think_t = float(diff.think_interval) * ms.rng.randf_range(0.8, 1.3)

	# 1) dunk when the lane is there
	if b._dunk_available() and openness > 60.0:
		it.shoot_pressed = true
		return
	# 2) take the open shot in range
	var want_three: bool = (
		dist > CourtGeometry.THREE_POINT_DIST and dist < 560.0
		and b.char_def.three_point >= 6
	)
	var in_range: bool = dist < 420.0 or want_three
	if in_range and openness > float(diff.open_shot_dist) \
			and ms.rng.randf() < float(diff.shoot_urge):
		it.shoot_pressed = true
		return
	# 3) hit a teammate who is clearly better placed
	var best = null
	var best_score := float(diff.pass_threshold)
	for tm in ms.teammates_of(b.team):
		if tm == b or tm.state == Baller.State.HURT:
			continue
		var tm_open: float = ms.nearest_opponent_distance(tm)
		var score: float = tm_open - openness \
			+ (dist - tm.position.distance_to(hoop)) * 0.35
		if score > best_score:
			best_score = score
			best = tm
	if best != null and ms.rng.randf() < 0.8:
		it.pass_pressed = true
		it.pass_target = best
		return
	# 4) pressured: jink sideways and burn turbo to create space
	if openness < 70.0:
		_strafe = 1.0 if ms.rng.randf() < 0.5 else -1.0
		_strafe_t = 0.4
		it.turbo = b.turbo_meter > 10.0


func _offense_off_ball(it: PlayerIntent, delta: float, ms) -> void:
	var b = baller
	_cut_timer -= delta
	_cutting_t -= delta
	if _cut_timer <= 0.0:
		_cut_timer = ms.rng.randf_range(2.5, 5.0)
		if ms.rng.randf() < 0.35:
			_cutting_t = 0.9  # backdoor cut to the rim
	var target: Vector2 = team_ai.offense_slot(b)
	if _cutting_t > 0.0:
		var hoop := CourtGeometry.hoop_pos(b.team)
		target = hoop + Vector2(-signf(hoop.x) * 90.0, b.position.y * 0.2)
		it.turbo = b.turbo_meter > 40.0
	_seek(it, target, 26.0)


func _defense(it: PlayerIntent, diff: Dictionary, delta: float, ms) -> void:
	var b = baller
	var mark = team_ai.defensive_mark(b)
	if mark == null:
		_seek(it, CourtGeometry.hoop_pos(1 - b.team), 120.0)
		return
	var my_hoop := CourtGeometry.hoop_pos(1 - b.team)  # the hoop we defend
	var guard_pos: Vector2 = mark.position \
		+ (my_hoop - mark.position).normalized() * 70.0
	_seek(it, guard_pos, 12.0)
	it.turbo = b.position.distance_to(guard_pos) > 260.0 and b.turbo_meter > 30.0
	if mark != ms.ball.holder:
		return
	var d: float = b.position.distance_to(mark.position)
	if mark.state == Baller.State.JUMP and mark.charging_shot and d < 95.0:
		# contest the shot
		if ms.rng.randf() < float(diff.block_urge):
			it.shoot_pressed = true
	elif d < 80.0 and ms.rng.randf() < float(diff.steal_rate) * delta:
		it.pass_pressed = true  # steal swipe (turbo = shove attempt)
		it.turbo = ms.rng.randf() < float(diff.shove_chance)


func _loose_ball(it: PlayerIntent, ms) -> void:
	var b = baller
	if team_ai.should_chase(b):
		_seek(it, ms.ball.position, 4.0)
		it.turbo = b.turbo_meter > 20.0
	else:
		# hedge back toward our hoop while the scramble resolves
		var my_hoop := CourtGeometry.hoop_pos(1 - b.team)
		_seek(it, (ms.ball.position + my_hoop) * 0.5, 60.0)


func _seek(it: PlayerIntent, target: Vector2, arrive_radius: float) -> void:
	var to_target: Vector2 = target - baller.position
	if to_target.length() > arrive_radius:
		it.move = to_target.normalized()
