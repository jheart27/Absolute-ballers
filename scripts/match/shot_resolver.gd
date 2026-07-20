class_name ShotResolver
## Decides a shot's fate at the instant of release — arcade determinism:
## outcome first, then the ball flight just sells the story.
## Inputs: meter timing quality, distance, shooter stats, defender pressure,
## fire bonus. Airborne defenders in range may flat-out reject it.


static func resolve(shooter, quality: float, match_scene) -> Dictionary:
	var hoop := CourtGeometry.hoop_pos(shooter.team)
	var dist: float = shooter.position.distance_to(hoop)
	var is_three := dist > CourtGeometry.THREE_POINT_DIST
	var rng: RandomNumberGenerator = match_scene.rng

	var pressure := 0.0
	for d in match_scene.opponents_of(shooter.team):
		var dd: float = d.position.distance_to(shooter.position)
		if dd < 110.0:
			pressure = maxf(pressure, (110.0 - dd) / 110.0 * 0.25)
		# a defender in the air next to the shooter is a live block window
		if d.state == Baller.State.JUMP and dd < 95.0 and d.z > 40.0:
			var block_chance: float = 0.30 + d.char_def.block * 0.05 \
				- (0.15 if shooter.on_fire else 0.0)
			if rng.randf() < block_chance:
				return {"blocked": true, "blocker": d}

	var base := 0.45
	if dist < 180.0:
		base = 0.78
	elif dist < 340.0:
		base = 0.60
	if is_three:
		base = 0.40
	var stat: int = shooter.char_def.three_point if is_three else shooter.char_def.dunk
	var p := base + stat * 0.012 + quality * 0.32 - pressure
	if shooter.on_fire:
		p += 0.22
	var made := rng.randf() < clampf(p, 0.05, 0.97)
	return {
		"blocked": false,
		"made": made,
		"points": 3 if is_three else 2,
		"hoop": hoop,
		"three": is_three,
	}
