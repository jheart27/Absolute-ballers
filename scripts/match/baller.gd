class_name Baller
extends Node2D
## One player pawn. All gameplay logic works off `intent` (PlayerIntent) —
## never raw Input — so humans, AI, and (post-v1) remote players are
## interchangeable. Sim state lives in plain fields and sim() is driven by
## MatchScene in a fixed order, which keeps the update deterministic-friendly
## for the future netcode split. Rendering is handled by the BallerVisual child.

enum State { IDLE, RUN, JUMP, DUNK, STEAL, HURT, CELEBRATE }

const TURBO_MULT := 1.3
const TURBO_DRAIN := 34.0
const TURBO_REGEN := 18.0
const JUMP_IMPULSE := 560.0
const AIR_DRIFT := 60.0
const STEAL_RANGE := 84.0
const STEAL_DURATION := 0.38
const HURT_DURATION := 1.0
const CELEBRATE_DURATION := 0.9

var char_def: CharacterDef
var team := 0
var match_scene = null  # MatchScene (untyped: cyclic reference)

# --- simulation state -------------------------------------------------------
var pos := Vector2.ZERO  # flat floor coords; node position is the projection
var z := 0.0
var zvel := 0.0
var vel := Vector2.ZERO
var state: int = State.IDLE
var state_t := 0.0
var facing := 1  # 1 right, -1 left
var stagger_t := 0.0  # recovery lockout (failed steal, landing, getting up)
var turbo_meter := 100.0
var on_fire := false
var charging_shot := false  # airborne with the ball, meter live
var post_dunk := false  # falling from the rim, keep the dunk pose
var dunk_from := Vector2.ZERO
var dunk_target := Vector2.ZERO
var dunk_duration := 0.6

# --- control ----------------------------------------------------------------
var controller = null  # active intent source (HumanInput or AIInput)
var ai_controller = null  # persistent AI brain, resumed when a human switches away
var intent: PlayerIntent = PlayerIntent.new()

# BallerVisual child. Created and attached by MatchScene, NOT here: the sim
# never references the visual's class, keeping the script dependency graph
# acyclic (cyclic class_name references can fail to resolve on a fresh
# project open, taking the whole autoload chain down with them).
var visual = null


func setup(def: CharacterDef, team_idx: int, match_ref) -> void:
	char_def = def
	team = team_idx
	match_scene = match_ref
	name = "Baller_%s" % def.id


func is_human() -> bool:
	return controller is HumanInput


func has_ball() -> bool:
	return match_scene.ball.holder == self


func run_speed() -> float:
	return 260.0 + char_def.speed * 7.0 + (55.0 if on_fire else 0.0)


func shot_quality() -> float:
	## 1.0 at the jump apex, falling off toward launch/landing.
	return 1.0 - clampf(absf(zvel) / JUMP_IMPULSE, 0.0, 1.0)


# --------------------------------------------------------------------- sim
func sim(delta: float) -> void:
	state_t += delta
	stagger_t = maxf(0.0, stagger_t - delta)
	match state:
		State.IDLE, State.RUN:
			_sim_ground(delta)
		State.JUMP:
			_sim_jump(delta)
		State.DUNK:
			_sim_dunk(delta)
		State.STEAL:
			_sim_steal(delta)
		State.HURT:
			if state_t >= HURT_DURATION:
				stagger_t = maxf(stagger_t, 0.2)
				_enter(State.IDLE)
		State.CELEBRATE:
			if state_t >= CELEBRATE_DURATION:
				_enter(State.IDLE)
	if not (intent.turbo and vel.length() > 10.0):
		turbo_meter = minf(100.0, turbo_meter + TURBO_REGEN * delta)
	position = CourtGeometry.project(pos)


func _sim_ground(delta: float) -> void:
	var mv := intent.move.limit_length(1.0)
	if stagger_t > 0.0:
		mv = Vector2.ZERO
	var speed := run_speed()
	var turbo_active: bool = intent.turbo and (turbo_meter > 0.0 or on_fire)
	if turbo_active and mv.length() > 0.1:
		speed *= TURBO_MULT
		if not on_fire:
			turbo_meter = maxf(0.0, turbo_meter - TURBO_DRAIN * delta)
	vel = mv * speed
	pos = CourtGeometry.clamp_to_floor(pos + vel * delta)
	if absf(mv.x) > 0.1:
		facing = 1 if mv.x > 0.0 else -1
	elif has_ball():
		facing = 1 if CourtGeometry.hoop_pos(team).x > pos.x else -1
	_enter(State.RUN if mv.length() > 0.1 else State.IDLE)
	if stagger_t > 0.0:
		return
	if intent.shoot_pressed:
		if has_ball():
			if _dunk_available():
				_start_dunk()
			else:
				_start_jump(true)
		else:
			_start_jump(false)  # defensive block jump
	elif intent.pass_pressed:
		if has_ball():
			match_scene.request_pass(self, intent)
		else:
			_attempt_steal()


func _start_jump(shooting: bool) -> void:
	charging_shot = shooting
	zvel = JUMP_IMPULSE
	vel = intent.move.limit_length(1.0) * run_speed() * 0.5  # carry some momentum
	AudioManager.play("whoosh", -14.0)
	_enter(State.JUMP)


func _sim_jump(delta: float) -> void:
	vel = vel.move_toward(Vector2.ZERO, 300.0 * delta)
	var drift := intent.move.limit_length(1.0) * AIR_DRIFT
	pos = CourtGeometry.clamp_to_floor(pos + (vel + drift) * delta)
	zvel -= CourtGeometry.GRAVITY * delta
	z += zvel * delta
	if charging_shot and (intent.shoot_released or (zvel < 0.0 and z < 30.0)):
		# releasing late is a forced brick, just like the arcades
		charging_shot = false
		match_scene.request_shot(self, shot_quality())
	if z <= 0.0:
		z = 0.0
		zvel = 0.0
		charging_shot = false
		post_dunk = false
		stagger_t = maxf(stagger_t, 0.12)
		_enter(State.IDLE)


func _dunk_available() -> bool:
	var reach := 150.0 + char_def.dunk * 12.0 + (90.0 if on_fire else 0.0)
	return pos.distance_to(CourtGeometry.hoop_pos(team)) < reach


func _start_dunk() -> void:
	var hoop := CourtGeometry.hoop_pos(team)
	dunk_from = pos
	dunk_target = hoop + Vector2(-28.0 * signf(hoop.x), 0.0)
	dunk_duration = clampf(dunk_from.distance_to(dunk_target) / 380.0, 0.5, 0.85)
	facing = 1 if dunk_target.x > pos.x else -1
	_enter(State.DUNK)


func _sim_dunk(_delta: float) -> void:
	var t := clampf(state_t / dunk_duration, 0.0, 1.0)
	pos = dunk_from.lerp(dunk_target, t)
	z = (CourtGeometry.RIM_HEIGHT + 30.0) * sin(t * PI * 0.5)
	if t >= 1.0:
		match_scene.complete_dunk(self)
		post_dunk = true  # free-fall from the rim keeping the dunk pose
		zvel = 0.0
		_enter(State.JUMP)


func _attempt_steal() -> void:
	facing = 1 if intent.move.x >= 0.0 else -1
	_enter(State.STEAL)
	var ball = match_scene.ball
	var victim = ball.holder
	if (
		victim == null
		or victim.team == team
		or victim.state != State.IDLE and victim.state != State.RUN
		or pos.distance_to(victim.pos) > STEAL_RANGE
	):
		stagger_t = 0.35  # whiffed swipe
		return
	facing = 1 if victim.pos.x > pos.x else -1
	var shove: bool = intent.turbo
	var chance: float = 0.30 + char_def.steal * 0.045 - victim.char_def.power * 0.02
	if shove:
		chance += 0.15
	if victim.on_fire:
		chance -= 0.12
	if match_scene.rng.randf() < clampf(chance, 0.05, 0.85):
		if shove:
			victim.knock_down()
		ball.poke_loose((pos.direction_to(victim.pos) + Vector2(0.0, 0.3)).normalized())
		EventBus.steal_made.emit(self, victim)
	else:
		stagger_t = 0.55


func _sim_steal(delta: float) -> void:
	pos = CourtGeometry.clamp_to_floor(
		pos + Vector2(facing * 120.0, 0.0) * delta)
	if state_t >= STEAL_DURATION:
		_enter(State.IDLE)


func knock_down() -> void:
	if state == State.DUNK:
		return  # dunks are armored — arcade rule
	z = 0.0
	zvel = 0.0
	charging_shot = false
	post_dunk = false
	_enter(State.HURT)
	EventBus.knockdown.emit(self)


func celebrate() -> void:
	if state == State.IDLE or state == State.RUN:
		_enter(State.CELEBRATE)


func reset_for_tip(p: Vector2) -> void:
	pos = p
	position = CourtGeometry.project(pos)
	z = 0.0
	zvel = 0.0
	vel = Vector2.ZERO
	stagger_t = 0.0
	charging_shot = false
	post_dunk = false
	state = State.IDLE
	state_t = 0.0
	facing = 1 if CourtGeometry.hoop_pos(team).x > pos.x else -1


func _enter(s: int) -> void:
	if state != s:
		state = s
		state_t = 0.0
