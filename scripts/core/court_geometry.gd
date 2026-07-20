class_name CourtGeometry
## World-space constants and the low-angle screen projection.
##
## The SIM lives in flat floor coordinates: x along the court, y depth,
## z height. Nothing in gameplay code ever sees the screen.
## RENDERING projects floor -> screen with depth compression (DEPTH_SCALE)
## and perspective x-foreshortening (far sideline narrower than near), which
## gives the Neo-Geo "low camera angle" look. Sprites y-sort by floor depth.
## tools/generate_placeholders.py mirrors these constants when painting the
## court, so art and gameplay always line up.

const HALF_LENGTH := 880.0
const HALF_DEPTH := 260.0
const HOOP_X := 780.0
const RIM_HEIGHT := 300.0
const RIM_RADIUS := 24.0
const THREE_POINT_DIST := 440.0
const GRAVITY := 1500.0

# --- projection (keep in sync with the art generator) ---
const DEPTH_SCALE := 0.62
const X_SCALE_FAR := 0.88
const X_SCALE_NEAR := 1.06


static func x_scale(depth_y: float) -> float:
	var t := (depth_y + HALF_DEPTH) / (HALF_DEPTH * 2.0)
	return lerpf(X_SCALE_FAR, X_SCALE_NEAR, t)


static func project(floor_pos: Vector2) -> Vector2:
	## Floor position -> screen position (z is applied by sprite offsets).
	return Vector2(floor_pos.x * x_scale(floor_pos.y), floor_pos.y * DEPTH_SCALE)


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
