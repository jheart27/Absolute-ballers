class_name MatchCamera
extends Camera2D
## Arcade framing for up to 10 ballers + ball: fit everyone in view, weight
## the center toward the ball, clamp to the arena art, and never zoom out
## past the sprite-readability floor. MIN_ZOOM guarantees a 96px sprite
## never renders below ~67px, and the projected arena art (court +
## parallax crowd) covers the whole reachable view.

const MIN_ZOOM := 0.7  # readability floor; also keeps view inside the art
const MAX_ZOOM := 1.0
const PAD := 190.0
const X_LIMIT := 1140.0  # horizontal art extent
const TOP_LIMIT := -760.0  # crowd covers up to here
const BOTTOM_LIMIT := 300.0  # front skirt covers down to here

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
	target.x = clampf(target.x, -X_LIMIT + half_view.x, X_LIMIT - half_view.x) \
		if half_view.x < X_LIMIT else 0.0
	if TOP_LIMIT + half_view.y < BOTTOM_LIMIT - half_view.y:
		target.y = clampf(
			target.y, TOP_LIMIT + half_view.y, BOTTOM_LIMIT - half_view.y)
	else:
		target.y = (TOP_LIMIT + BOTTOM_LIMIT) * 0.5

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
