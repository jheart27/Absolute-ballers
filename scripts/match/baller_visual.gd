class_name BallerVisual
extends Node2D
## Renders a Baller: sprite animation, team ring, control arrow, shadow,
## fire aura, shot meter, turbo bar. Pure read-only view of the sim state —
## it never mutates the baller. Swapping in final art touches nothing here
## (sheets are resolved via CharacterDef + BallerAnim).

const SPRITE_FEET_OFFSET := 28.0  # feet sit at y=60 in a 64-tall centered frame

var baller = null
var team_color := Color.WHITE

var _sprite: AnimatedSprite2D
var _aura: AnimatedSprite2D
var _ring: Sprite2D
var _arrow: Sprite2D
var _shadow: Sprite2D
var _embers: CPUParticles2D


func setup(b, team_col: Color) -> void:
	baller = b
	team_color = team_col
	_ring = Sprite2D.new()
	_ring.texture = Art.tex("res://assets/placeholder/fx/ring.png")
	_ring.modulate = team_color
	_ring.position = Vector2(0.0, 4.0)
	add_child(_ring)
	_shadow = Sprite2D.new()
	_shadow.texture = Art.tex("res://assets/placeholder/fx/shadow.png")
	add_child(_shadow)
	_aura = AnimatedSprite2D.new()
	_aura.sprite_frames = BallerAnim.build_simple_strip(
		"res://assets/placeholder/fx/fire_aura.png", 96, 10.0)
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
	add_child(_embers)
	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = BallerAnim.build_frames(b.char_def.sprite_sheet)
	_sprite.play("idle")
	add_child(_sprite)
	_arrow = Sprite2D.new()
	_arrow.texture = Art.tex("res://assets/placeholder/fx/arrow.png")
	_arrow.visible = false
	add_child(_arrow)


func _process(_delta: float) -> void:
	var zoff: float = -SPRITE_FEET_OFFSET - baller.z
	_sprite.position = Vector2(0.0, zoff)
	_sprite.flip_h = baller.facing < 0
	_aura.position = Vector2(0.0, zoff - 6.0)
	_aura.visible = baller.on_fire
	_embers.emitting = baller.on_fire
	_embers.position = Vector2(0.0, zoff)
	_shadow.scale = Vector2.ONE * lerpf(1.0, 0.6, clampf(baller.z / 300.0, 0.0, 1.0))
	var human: bool = baller.is_human()
	_arrow.visible = human
	if human:
		_arrow.modulate = baller.controller.color
		_arrow.position = Vector2(0.0, zoff - 46.0)
		_ring.modulate = baller.controller.color
	else:
		_ring.modulate = team_color
	_update_anim()
	queue_redraw()


func _update_anim() -> void:
	var has_ball: bool = baller.has_ball()
	var want := "idle"
	match baller.state:
		Baller.State.IDLE:
			want = "dribble" if has_ball else "idle"
		Baller.State.RUN:
			want = "dribble" if has_ball else "run"
		Baller.State.JUMP:
			if baller.post_dunk:
				want = "dunk"
			elif has_ball or baller.charging_shot:
				want = "jump_shot"
			else:
				want = "block"
		Baller.State.DUNK:
			want = "dunk"
		Baller.State.STEAL:
			want = "steal"
		Baller.State.HURT:
			want = "hurt"
		Baller.State.CELEBRATE:
			want = "celebrate"
	if _sprite.animation != want:
		_sprite.play(want)


func _draw() -> void:
	# shot-timing meter above the head while a shot is charging
	if baller.charging_shot:
		var q: float = baller.shot_quality()
		var w := 44.0
		var y: float = -SPRITE_FEET_OFFSET - baller.z - 60.0
		draw_rect(Rect2(-w * 0.5, y, w, 7.0), Color(0.0, 0.0, 0.0, 0.65))
		draw_rect(
			Rect2(-w * 0.5 + 1.0, y + 1.0, (w - 2.0) * q, 5.0),
			Color(1.0 - q, q, 0.15))
	# turbo bar for human seats
	if baller.is_human() and baller.turbo_meter < 99.5:
		draw_rect(Rect2(-20.0, 12.0, 40.0, 4.0), Color(0.0, 0.0, 0.0, 0.55))
		draw_rect(
			Rect2(-19.0, 13.0, 38.0 * baller.turbo_meter / 100.0, 2.0),
			baller.controller.color)
