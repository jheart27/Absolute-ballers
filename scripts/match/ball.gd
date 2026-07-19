class_name GameBall
extends Node2D
## The ball's simulation + visual. Arcade model: a shot's outcome is decided
## at release (ShotResolver) and the flight animation sells it; passes fly
## point-to-point with interception rolls; loose balls bounce with simple
## z-physics. sim() is driven by MatchScene after all ballers.

enum State { HELD, SHOT, PASS, LOOSE }

const PICKUP_RADIUS := 36.0
const PASS_SPEED := 950.0

var match_scene = null
var state: int = State.LOOSE
var holder = null
var z := 20.0
var zvel := 0.0
var vel := Vector2.ZERO
var pickup_cooldown := 0.0

# shot flight
var flight_from := Vector2.ZERO
var flight_from_z := 0.0
var flight_target := Vector2.ZERO
var flight_dur := 0.9
var flight_t := 0.0
var flight_apex := 140.0
var shot_will_score := false
var shot_points := 2
var shooter = null

# pass flight
var pass_receiver = null
var pass_team := 0
var _pass_rolled: Array = []  # opponents who already had their interception roll

var _spin_t := 0.0
var _held_prev_z := 0.0
var _sprite: AnimatedSprite2D
var _shadow: Sprite2D
var _embers: CPUParticles2D


func setup(match_ref) -> void:
	match_scene = match_ref
	name = "Ball"
	_shadow = Sprite2D.new()
	_shadow.texture = Art.tex("res://assets/placeholder/fx/shadow.png")
	_shadow.scale = Vector2(0.6, 0.6)
	add_child(_shadow)
	_embers = CPUParticles2D.new()
	_embers.emitting = false
	_embers.amount = 26
	_embers.lifetime = 0.5
	_embers.local_coords = false
	_embers.direction = Vector2(0.0, -1.0)
	_embers.spread = 180.0
	_embers.initial_velocity_min = 20.0
	_embers.initial_velocity_max = 70.0
	_embers.gravity = Vector2(0.0, -40.0)
	_embers.scale_amount_min = 2.0
	_embers.scale_amount_max = 4.0
	_embers.color = Color(1.0, 0.55, 0.1, 0.85)
	add_child(_embers)
	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = BallerAnim.build_simple_strip(
		"res://assets/placeholder/fx/ball.png", 16, 12.0)
	_sprite.scale = Vector2(2.0, 2.0)
	_sprite.play("loop")
	add_child(_sprite)


func _process(_delta: float) -> void:
	_sprite.position = Vector2(0.0, -z - 12.0)
	_shadow.scale = Vector2.ONE * lerpf(0.6, 0.35, clampf(z / 300.0, 0.0, 1.0))
	_sprite.speed_scale = 2.0 if state == State.SHOT or state == State.PASS else 1.0
	# she's on fire -> so is the ball
	var hot: bool = (
		(holder != null and holder.on_fire)
		or (state == State.SHOT and shooter != null and shooter.on_fire)
	)
	_sprite.modulate = Color(1.0, 0.6, 0.25) if hot else Color.WHITE
	_embers.emitting = hot
	_embers.position = _sprite.position


# --------------------------------------------------------------------- sim
func sim(delta: float) -> void:
	_spin_t += delta
	pickup_cooldown = maxf(0.0, pickup_cooldown - delta)
	match state:
		State.HELD:
			_sim_held()
		State.SHOT:
			_sim_shot(delta)
		State.PASS:
			_sim_pass(delta)
		State.LOOSE:
			_sim_loose(delta)


func _sim_held() -> void:
	if holder == null or holder.state == Baller.State.HURT:
		var rng: RandomNumberGenerator = match_scene.rng
		poke_loose(Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.0, 1.0)).normalized())
		return
	position = holder.position + Vector2(holder.facing * 18.0, 2.0)
	if holder.z > 0.0:
		z = holder.z + 48.0
	elif holder.vel.length() > 20.0:
		z = absf(sin(_spin_t * 9.0)) * 40.0 + 10.0  # hard dribble on the move
	else:
		z = absf(sin(_spin_t * 5.0)) * 26.0 + 10.0
	if z < 14.0 and _held_prev_z >= 14.0 and holder.z <= 0.0:
		AudioManager.play("dribble", -16.0)
	_held_prev_z = z


func give_to(baller) -> void:
	holder = baller
	state = State.HELD
	shooter = null
	pass_receiver = null
	match_scene.on_possession(baller)


func launch_shot(by, result: Dictionary) -> void:
	shooter = by
	holder = null
	state = State.SHOT
	flight_from = position
	flight_from_z = z
	shot_will_score = result.made
	shot_points = result.points
	var hoop: Vector2 = result.hoop
	if shot_will_score:
		flight_target = hoop
	else:
		var rng: RandomNumberGenerator = match_scene.rng
		var ang := rng.randf_range(0.0, TAU)
		flight_target = hoop + Vector2(cos(ang), sin(ang) * 0.5) * CourtGeometry.RIM_RADIUS
	flight_t = 0.0
	var dist := position.distance_to(hoop)
	flight_dur = clampf(dist / 640.0, 0.55, 1.05)
	flight_apex = 120.0 + dist * 0.16


func _sim_shot(delta: float) -> void:
	flight_t += delta / flight_dur
	var t := clampf(flight_t, 0.0, 1.0)
	position = flight_from.lerp(flight_target, t)
	z = lerpf(flight_from_z, CourtGeometry.RIM_HEIGHT, t) + flight_apex * 4.0 * t * (1.0 - t)
	if flight_t < 1.0:
		return
	if shot_will_score:
		# swish: MatchScene scores it and hands the ball to the other team
		match_scene.score_basket(shooter.team, shot_points, shooter, false)
	else:
		# rim clank -> live rebound (no stoppage, ever)
		AudioManager.play("rim_clank", -6.0)
		var rng: RandomNumberGenerator = match_scene.rng
		vel = Vector2(
			-signf(flight_target.x) * rng.randf_range(60.0, 240.0),
			rng.randf_range(-170.0, 170.0))
		zvel = rng.randf_range(150.0, 330.0)
		state = State.LOOSE
		pickup_cooldown = 0.15


func launch_pass(from_baller, to_baller) -> void:
	holder = null
	state = State.PASS
	pass_receiver = to_baller
	pass_team = from_baller.team
	_pass_rolled = []
	z = maxf(z, 40.0)


func _sim_pass(delta: float) -> void:
	if pass_receiver == null or not is_instance_valid(pass_receiver):
		_drop_dead()
		return
	z = lerpf(z, 60.0, 6.0 * delta)
	# defenders sitting in the passing lane get one interception roll each
	var rng: RandomNumberGenerator = match_scene.rng
	for opp in match_scene.opponents_of(pass_team):
		if _pass_rolled.has(opp) or opp.state == Baller.State.HURT:
			continue
		if opp.position.distance_to(position) < 42.0 and z < 110.0:
			_pass_rolled.append(opp)
			if rng.randf() < 0.22 + opp.char_def.steal * 0.035:
				give_to(opp)
				EventBus.steal_made.emit(opp, null)
				return
	var to_target := pass_receiver.position - position
	var step := PASS_SPEED * delta
	if to_target.length() <= step:
		if pass_receiver.state == Baller.State.HURT:
			_drop_dead()
		else:
			var receiver = pass_receiver
			give_to(receiver)
			match_scene.on_pass_caught(receiver)
		return
	position += to_target.normalized() * step


func _drop_dead() -> void:
	state = State.LOOSE
	vel = Vector2.ZERO
	zvel = 0.0


func poke_loose(dir: Vector2) -> void:
	holder = null
	state = State.LOOSE
	vel = dir * 220.0
	z = maxf(z, 30.0)
	zvel = 120.0
	pickup_cooldown = 0.18


func tip_toss() -> void:
	## Jump-ball toss at center court (match start / overtime).
	holder = null
	shooter = null
	pass_receiver = null
	state = State.LOOSE
	position = Vector2.ZERO
	vel = Vector2.ZERO
	z = 20.0
	zvel = 720.0
	pickup_cooldown = 0.55


func _sim_loose(delta: float) -> void:
	position += vel * delta
	vel = vel.move_toward(Vector2.ZERO, 260.0 * delta)
	zvel -= CourtGeometry.GRAVITY * delta
	z += zvel * delta
	if z <= 0.0:
		z = 0.0
		if zvel < -140.0:
			AudioManager.play("bounce", -10.0)
		zvel = -zvel * 0.55
		if zvel < 60.0:
			zvel = 0.0
	# soft walls at the apron edge — the ball never goes out of bounds
	if absf(position.x) > CourtGeometry.HALF_LENGTH + 40.0:
		position.x = signf(position.x) * (CourtGeometry.HALF_LENGTH + 40.0)
		vel.x = -vel.x * 0.6
	if absf(position.y) > CourtGeometry.HALF_DEPTH + 40.0:
		position.y = signf(position.y) * (CourtGeometry.HALF_DEPTH + 40.0)
		vel.y = -vel.y * 0.6
	if pickup_cooldown > 0.0 or z > 95.0:
		return
	for b in match_scene.all_ballers:
		if b.state == Baller.State.HURT or b.state == Baller.State.DUNK:
			continue
		if b.position.distance_to(position) < PICKUP_RADIUS:
			give_to(b)
			return
