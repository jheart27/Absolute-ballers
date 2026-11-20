class_name BallerVisual
extends Node2D
## Renders a Baller: sprite animation in team colors, team ring, control
## arrow, shadow, fire aura, shot meter, turbo bar. Pure read-only view of the
## sim state — it never mutates the baller.
##
## Sheets come from CharacterDef and follow the generated BallerSheet
## contract. Looping moves play on their own; one-shot moves are scrubbed
## from the sim's clocks so the key frames (shot release at the jump apex,
## the slam at the rim) land exactly when the sim does them.

const KIT_SHADER := preload("res://scripts/match/baller_kit.gdshader")
const ART_TOP := 186.0  # top of the art above the feet; arrow + meter sit over it
const SHADOW_SCALE := 1.5
const RING_SCALE := 1.4
const RELEASE_TIME := 0.16  # flick + follow-through after the ball leaves her hand

var baller = null
var team_color := Color.WHITE

var _sprite: AnimatedSprite2D
var _aura: AnimatedSprite2D
var _ring: Sprite2D
var _arrow: Sprite2D
var _shadow: Sprite2D
var _embers: CPUParticles2D
var _ds := 1.0  # depth scale of the current frame
var _was_jumping := false
var _shot_jump := false  # this jump started as a jump shot
var _release_t := -1.0  # state_t when the shot left her hand
var _fall_time := 0.5  # post-dunk drop duration, measured when it starts


func setup(b, team_col: Color) -> void:
	baller = b
	team_color = team_col
	_ring = Sprite2D.new()
	_ring.texture = Art.tex("res://assets/placeholder/fx/ring.png")
	_ring.modulate = team_color
	_ring.position = Vector2(0.0, 4.0)
	_ring.scale = Vector2.ONE * RING_SCALE
	add_child(_ring)
	_shadow = Sprite2D.new()
	_shadow.texture = Art.tex("res://assets/placeholder/fx/shadow.png")
	add_child(_shadow)
	_aura = AnimatedSprite2D.new()
	_aura.sprite_frames = BallerAnim.build_simple_strip(
		"res://assets/fx/fire_aura.png", BallerSheet.FRAME_SIZE.x, BallerSheet.AURA_FPS)
	_aura.centered = false
	_aura.offset = -BallerSheet.FEET
	_aura.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	_aura.play("loop")
	_aura.visible = false
	add_child(_aura)
	_embers = CPUParticles2D.new()
	_embers.emitting = false
	_embers.amount = 18
	_embers.lifetime = 0.45
	_embers.local_coords = false  # embers trail behind a sprinting baller
	_embers.direction = Vector2(0.0, -1.0)
	_embers.spread = 180.0
	_embers.initial_velocity_min = 12.0
	_embers.initial_velocity_max = 50.0
	_embers.gravity = Vector2(0.0, -35.0)
	_embers.scale_amount_min = 1.5
	_embers.scale_amount_max = 3.0
	_embers.color = Color(1.0, 0.55, 0.1, 0.7)
	_embers.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_embers.emission_rect_extents = Vector2(26.0, 60.0)
	add_child(_embers)
	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = BallerAnim.build_frames(b.char_def.sprite_sheet)
	# origin at the feet: scaling and flipping happen around where she stands
	_sprite.centered = false
	_sprite.offset = -BallerSheet.FEET
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	if b.char_def.kit_sheet != "":
		var mat := ShaderMaterial.new()
		mat.shader = KIT_SHADER
		mat.set_shader_parameter("kit_tex", Art.tex(b.char_def.kit_sheet))
		mat.set_shader_parameter("team_color", team_color)
		mat.set_shader_parameter("kit_base", BallerSheet.KIT_BASE)
		_sprite.material = mat
	_sprite.play("idle")
	add_child(_sprite)
	_arrow = Sprite2D.new()
	_arrow.texture = Art.tex("res://assets/placeholder/fx/arrow.png")
	_arrow.visible = false
	add_child(_arrow)


func _process(_delta: float) -> void:
	# depth scale: players toward the far sideline render a touch smaller,
	# reinforcing the low camera angle (matches the court's x-foreshortening)
	_ds = lerpf(0.9, 1.06, clampf(
		(baller.pos.y + CourtGeometry.HALF_DEPTH) / (CourtGeometry.HALF_DEPTH * 2.0),
		0.0, 1.0))
	var lift := Vector2(0.0, -baller.z)
	_sprite.scale = Vector2(_ds, _ds)
	_sprite.position = lift
	_sprite.flip_h = baller.facing < 0
	_aura.scale = _sprite.scale
	_aura.position = lift
	_aura.flip_h = _sprite.flip_h
	_aura.visible = baller.on_fire
	_embers.emitting = baller.on_fire
	_embers.position = lift + Vector2(0.0, -70.0 * _ds)
	_shadow.scale = Vector2.ONE * SHADOW_SCALE * lerpf(
		1.0, 0.6, clampf(baller.z / 300.0, 0.0, 1.0))
	var human: bool = baller.is_human()
	_arrow.visible = human
	if human:
		_arrow.modulate = baller.controller.color
		_arrow.position = lift + Vector2(0.0, -(ART_TOP + 10.0) * _ds)
		_ring.modulate = baller.controller.color
	else:
		_ring.modulate = team_color
	_update_anim()
	queue_redraw()


func ball_anchor() -> Variant:
	## Where the ball sits in her hand in the frame on screen, relative to the
	## baller node; null when this frame has no ball in hand. GameBall snaps
	## its sprite here so the ball always meets the hand that's drawn.
	var off: Variant = BallerAnim.ball_offset(_sprite.animation, _sprite.frame)
	if off == null:
		return null
	var o: Vector2 = off
	return Vector2(o.x * float(baller.facing), o.y) * _ds + Vector2(0.0, -baller.z)


func _apex_time() -> float:
	return Baller.JUMP_IMPULSE / CourtGeometry.GRAVITY


func _update_anim() -> void:
	var jumping: bool = baller.state == Baller.State.JUMP
	if jumping and not _was_jumping:
		_shot_jump = baller.charging_shot
		_release_t = -1.0
		_fall_time = maxf(0.2, sqrt(2.0 * maxf(baller.z, 1.0) / CourtGeometry.GRAVITY))
	_was_jumping = jumping
	var has_ball: bool = baller.has_ball()
	match baller.state:
		Baller.State.IDLE:
			_loop("hold" if has_ball else "idle")
		Baller.State.RUN:
			_loop("dribble" if has_ball else "run")
		Baller.State.JUMP:
			if baller.post_dunk:  # dropping from the rim after the slam
				var slam: float = BallerAnim.mark("dunk")
				_scrub("dunk", slam + (1.0 - slam) * clampf(baller.state_t / _fall_time, 0.0, 1.0))
			elif _shot_jump:
				var release: float = BallerAnim.mark("jump_shot")
				if baller.charging_shot:  # rise to the set point, hold it at the apex
					_scrub("jump_shot", release * clampf(baller.state_t / _apex_time(), 0.0, 1.0))
				else:
					if _release_t < 0.0:
						_release_t = baller.state_t
					_scrub("jump_shot", release + (1.0 - release) * clampf(
						(baller.state_t - _release_t) / RELEASE_TIME, 0.0, 1.0))
			else:  # defensive jump: hands up at the apex
				_scrub("block", clampf(baller.state_t / (_apex_time() * 1.5), 0.0, 1.0))
		Baller.State.DUNK:
			_scrub("dunk", BallerAnim.mark("dunk") * clampf(
				baller.state_t / maxf(baller.dunk_duration, 0.01), 0.0, 1.0))
		Baller.State.STEAL:
			_scrub("steal", clampf(baller.state_t / Baller.STEAL_DURATION, 0.0, 1.0))
		Baller.State.HURT:
			_scrub("hurt", clampf(baller.state_t / Baller.HURT_DURATION, 0.0, 1.0))
		Baller.State.CELEBRATE:
			_loop("celebrate")


func _loop(anim: String) -> void:
	if _sprite.animation != anim or not _sprite.is_playing():
		_sprite.play(anim)


func _scrub(anim: String, t: float) -> void:
	if _sprite.animation != anim:
		_sprite.animation = anim
	if _sprite.is_playing():
		_sprite.pause()
	_sprite.frame = BallerAnim.frame_at(anim, t)


func _draw() -> void:
	# shot-timing meter above the head while a shot is charging
	if baller.charging_shot:
		var q: float = baller.shot_quality()
		var w := 52.0
		var y: float = -baller.z - (ART_TOP + 26.0) * _ds
		draw_rect(Rect2(-w * 0.5, y, w, 8.0), Color(0.0, 0.0, 0.0, 0.65))
		draw_rect(
			Rect2(-w * 0.5 + 1.0, y + 1.0, (w - 2.0) * q, 6.0),
			Color(1.0 - q, q, 0.15))
	# turbo bar for human seats
	if baller.is_human() and baller.turbo_meter < 99.5:
		draw_rect(Rect2(-24.0, 14.0, 48.0, 5.0), Color(0.0, 0.0, 0.0, 0.55))
		draw_rect(
			Rect2(-23.0, 15.0, 46.0 * baller.turbo_meter / 100.0, 3.0),
			baller.controller.color)
