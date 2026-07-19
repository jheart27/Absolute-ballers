class_name CourtGeometry
## World-space constants. 1 world unit = 1 pixel of the placeholder court art.
## x runs along the court, y is depth (screen-down), z is height (jump/ball arc).
## Screen position of anything airborne = (x, y - z), y-sorted by floor y.

const HALF_LENGTH := 880.0
const HALF_DEPTH := 260.0
const HOOP_X := 780.0
const RIM_HEIGHT := 300.0
const RIM_RADIUS := 24.0
const THREE_POINT_DIST := 440.0
const GRAVITY := 1500.0


static func hoop_pos(team_attacking: int) -> Vector2:
	# Team 0 attacks the right hoop, team 1 the left.
	return Vector2(HOOP_X if team_attacking == 0 else -HOOP_X, 0.0)


static func clamp_to_floor(p: Vector2) -> Vector2:
	return Vector2(
		clampf(p.x, -HALF_LENGTH, HALF_LENGTH),
		clampf(p.y, -HALF_DEPTH, HALF_DEPTH)
	)


static func is_three(from_pos: Vector2, hoop: Vector2) -> bool:
	return from_pos.distance_to(hoop) > THREE_POINT_DIST
