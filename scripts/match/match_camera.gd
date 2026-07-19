class_name MatchCamera
extends Camera2D
## Arcade framing for up to 10 ballers + ball: fit everyone in view, weight
## the center toward the ball, clamp to the court art, and never zoom out
## past the sprite-readability floor. This is the "camera is a core design
## problem" answer: MIN_ZOOM guarantees a 64px sprite never renders below
## ~40px, and the court art extends far enough (2048x1280) that max zoom-out
## still shows arena, not void.

const MIN_ZOOM := 0.63  # readability floor; also keeps view inside the art
const MAX_ZOOM := 1.05
const PAD := 170.0
const ART_HALF := Vector2(1024.0, 640.0)

var match_scene = null
var _shake := 0.0


func add_shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


func _process(delta: float) -> void:
	if match_scene == null or match_scene.all_ballers.is_empty():
		return
	var ball = match_scene.ball
	var lo := Vector2(INF, INF)
	var hi := Vector2(-INF, -INF)
	var points: Array = []
	for b in match_scene.all_ballers:
		points.append(Vector2(b.position.x, b.position.y - b.z))
	points.append(Vector2(ball.position.x, ball.position.y - ball.z))
	for p in points:
		lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.y))
		hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.y))
	lo -= Vector2(PAD, PAD + 130.0)  # extra headroom for shot arcs
	hi += Vector2(PAD, PAD * 0.7)
	var box := hi - lo
	var vp := get_viewport_rect().size
	var k := minf(vp.x / maxf(box.x, 1.0), vp.y / maxf(box.y, 1.0))
	k = clampf(k, MIN_ZOOM, MAX_ZOOM)

	var centroid := (lo + hi) * 0.5
	var ball_screen := Vector2(ball.position.x, ball.position.y - ball.z * 0.5)
	var target := centroid.lerp(ball_screen, 0.45)
	var half_view := vp * 0.5 / k
	target.x = clampf(target.x, -ART_HALF.x + half_view.x, ART_HALF.x - half_view.x) \
		if half_view.x < ART_HALF.x else 0.0
	target.y = clampf(target.y, -ART_HALF.y + half_view.y, ART_HALF.y - half_view.y) \
		if half_view.y < ART_HALF.y else 0.0

	position = position.lerp(target, 1.0 - exp(-6.0 * delta))
	var kz := lerpf(zoom.x, k, 1.0 - exp(-3.5 * delta))
	zoom = Vector2(kz, kz)
	if _shake > 0.0:
		offset = Vector2(
			randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * _shake
		_shake *= exp(-7.0 * delta)
		if _shake < 0.4:
			_shake = 0.0
			offset = Vector2.ZERO
