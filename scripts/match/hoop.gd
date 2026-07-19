class_name Hoop
extends Node2D
## One basket. `attacked_by` is the team that scores here (team 0 attacks the
## right hoop). Placeholder art is drawn as the LEFT-court hoop (rim pointing
## right); the right hoop is the same texture flipped.
## In hoop.png the rim center is pixel (76, 100) and the floor is y=400 —
## keep that alignment if you replace the art.

const RIM_PX := Vector2(76.0, 100.0)
const ART_SIZE := Vector2(128.0, 400.0)

var attacked_by := 0
var _sprite: Sprite2D


func setup(team_attacking: int) -> void:
	attacked_by = team_attacking
	position = CourtGeometry.hoop_pos(team_attacking)
	name = "Hoop_%d" % team_attacking
	_sprite = Sprite2D.new()
	_sprite.texture = Art.tex("res://assets/placeholder/court/hoop.png")
	_sprite.centered = false
	if position.x > 0.0:
		_sprite.flip_h = true
		_sprite.offset = Vector2(-(ART_SIZE.x - RIM_PX.x), -ART_SIZE.y)
	else:
		_sprite.offset = Vector2(-RIM_PX.x, -ART_SIZE.y)
	add_child(_sprite)


func flash() -> void:
	_sprite.modulate = Color(2.2, 2.2, 2.2)
	var tw := create_tween()
	tw.tween_property(_sprite, "modulate", Color.WHITE, 0.35)
