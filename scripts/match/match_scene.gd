class_name MatchScene
extends Node2D
## Builds and runs one match from a MatchConfig: court, hoops, ball, ballers,
## team AIs, camera, HUD. Owns the fixed-order sim loop (AI coordinators ->
## intents -> switching -> ballers -> ball -> clock) so the whole game step
## is a single deterministic-friendly function of intents — the seam the
## post-v1 netcode will slot into.

var config: MatchConfig
var settings: MatchSettings
var state: MatchState
var rng := RandomNumberGenerator.new()

var ball: GameBall
var hoops: Array = []  # hoops[t] = hoop attacked by team t
var all_ballers: Array = []
var team_ballers: Array = [[], []]
var team_ais: Array = []
var humans: Array = []  # HumanInput seats
var hud: MatchHUD
var cam: MatchCamera

var _stage: Node2D
var _crowd: Sprite2D
var _crowd_base := Vector2.ZERO
var _break_t := 0.0
var attract := false  # AI-vs-AI demo: any button exits
var _any_prev := true  # swallow the press that launched the demo
var _auto_switch_from = null  # human passer awaiting control-follows-ball
var _pause_prev := {}


func _ready() -> void:
	config = Game.pending_match
	if config == null:
		config = MatchConfig.quick_default(
			Game.settings, Game.teams, Game.character_list())
	settings = config.settings
	attract = config.human_seats.is_empty() and config.context == "exhibition"
	rng.randomize()
	_build_court()
	_build_teams()
	state = MatchState.new(settings)
	state.ballers = all_ballers
	cam = MatchCamera.new()
	cam.match_scene = self
	add_child(cam)
	cam.make_current()
	hud = MatchHUD.new()
	hud.match_scene = self
	add_child(hud)
	_reset_formation(0, true)  # quarter 1 opens with a jump-ball toss
	EventBus.steal_made.connect(_on_steal_made)
	EventBus.knockdown.connect(_on_knockdown)
	EventBus.shot_blocked.connect(_on_shot_blocked)
	EventBus.quarter_started.emit(1)
	EventBus.announce.emit("TIP-OFF!", 0)
	AudioManager.start_ambient()


func _exit_tree() -> void:
	AudioManager.stop_ambient()
	Engine.time_scale = 1.0  # never leak a hit-stop into the menus
	if EventBus.steal_made.is_connected(_on_steal_made):
		EventBus.steal_made.disconnect(_on_steal_made)
	if EventBus.knockdown.is_connected(_on_knockdown):
		EventBus.knockdown.disconnect(_on_knockdown)
	if EventBus.shot_blocked.is_connected(_on_shot_blocked):
		EventBus.shot_blocked.disconnect(_on_shot_blocked)


func _on_steal_made(stealer, _victim) -> void:
	if stealer != null:
		state.add_steal(stealer)
	if rng.randf() < 0.6:
		EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.STEAL, rng), 1)


func _on_shot_blocked(blocker, shooter) -> void:
	## Fires for both release blocks (ShotResolver) and mid-flight goaltend
	## swats (GameBall) — all the presentation lives here, once.
	state.add_block(blocker)
	EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.BLOCK, rng), 2)
	cam.add_shake(8.0)
	_rumble(shooter, 0.3, 0.5, 0.25)
	_hitstop(0.07)


func _hitstop(duration: float) -> void:
	## Tiny freeze-frame for big moments. The restore lambda captures no
	## nodes, so a mid-hitstop scene change can't strand a slow time scale
	## (and _exit_tree restores it as a belt-and-braces).
	Engine.time_scale = 0.12
	get_tree().create_timer(duration, true, false, true).timeout.connect(
		func() -> void: Engine.time_scale = 1.0)


func _on_knockdown(victim) -> void:
	EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.KNOCKDOWN, rng), 1)
	cam.add_shake(10.0)
	_rumble(victim, 0.8, 0.9, 0.4)


func _rumble(baller, weak: float, strong: float, duration: float) -> void:
	if baller == null or not (baller.controller is HumanInput):
		return
	var dev: int = baller.controller.device
	if dev == -2:
		var pads := Input.get_connected_joypads()
		if pads.is_empty():
			return
		dev = pads[0]
	if dev >= 0:
		Input.start_joy_vibration(dev, weak, strong, duration)


const CROWD_PARALLAX := Vector2(0.42, 0.75)  # screen-speed factor (<1 = far)


func _build_court() -> void:
	_crowd = Sprite2D.new()
	_crowd.texture = Art.tex("res://assets/placeholder/court/crowd.png")
	# bottom of the crowd wall meets the far edge of the projected floor
	_crowd_base = Vector2(
		0.0,
		CourtGeometry.project(Vector2(0.0, -CourtGeometry.HALF_DEPTH)).y
		- _crowd.texture.get_height() * 0.5 + 10.0)
	_crowd.position = _crowd_base
	add_child(_crowd)
	var floor_sprite := Sprite2D.new()
	floor_sprite.texture = Art.tex("res://assets/placeholder/court/court_full.png")
	add_child(floor_sprite)
	_stage = Node2D.new()
	_stage.name = "Stage"
	_stage.y_sort_enabled = true
	add_child(_stage)
	for t in 2:
		var hoop := Hoop.new()
		_stage.add_child(hoop)
		hoop.setup(t)
		hoops.append(hoop)
	ball = GameBall.new()
	_stage.add_child(ball)
	ball.setup(self)


func _process(_delta: float) -> void:
	# parallax: the crowd tracks a fraction of the camera motion so it reads
	# as far away (screen speed = CROWD_PARALLAX * normal)
	if cam == null or _crowd == null:
		return
	_crowd.position = _crowd_base + Vector2(
		cam.position.x * (1.0 - CROWD_PARALLAX.x),
		cam.position.y * (1.0 - CROWD_PARALLAX.y))


func _build_teams() -> void:
	for t in 2:
		var team_ai := TeamAI.new(t, config.ai_levels[t], self)
		team_ais.append(team_ai)
		var team_def: TeamDef = config.team_defs[t]
		for char_def in config.rosters[t]:
			var b := Baller.new()
			_stage.add_child(b)
			b.setup(char_def, t, self)
			var vis := BallerVisual.new()
			b.add_child(vis)
			vis.setup(b, team_def.primary_color)
			b.visual = vis
			b.ai_controller = AIInput.new(b, team_ai)
			b.controller = b.ai_controller
			team_ballers[t].append(b)
			all_ballers.append(b)
	for seat in config.human_seats:
		var h := HumanInput.new(seat.device, seat.seat)
		humans.append(h)
		var b = team_ballers[seat.team][seat.char_index]
		b.controller = h


func _reset_formation(possession_team: int, tip := false) -> void:
	for t in 2:
		var side := -1.0 if t == 0 else 1.0  # team 0 starts on the left half
		var n: int = team_ballers[t].size()
		for i in n:
			team_ballers[t][i].reset_for_tip(Vector2(
				side * (140.0 + 130.0 * i),
				(i - (n - 1) * 0.5) * 150.0))
	if tip:
		ball.tip_toss()  # live scramble — nearest ballers fight for it
	else:
		ball.give_to(team_ballers[possession_team][0])


# -------------------------------------------------------------------- loop
func _physics_process(delta: float) -> void:
	if attract:
		var any_now := Input.is_anything_pressed()
		if any_now and not _any_prev:
			Game.finish_match(state.leader())
			return
		_any_prev = any_now
	if state.phase == MatchState.Phase.ENDED:
		return
	_poll_pause()
	if state.phase == MatchState.Phase.QUARTER_BREAK:
		_break_t -= delta
		if _break_t <= 0.0:
			_begin_quarter()
		return
	for team_ai in team_ais:
		team_ai.update(delta)
	for b in all_ballers:
		b.intent = b.controller.poll(delta)
	for b in all_ballers:
		if b.intent.switch_pressed and b.controller is HumanInput:
			_switch_human(b)
	for b in all_ballers:
		b.sim(delta)
	ball.sim(delta)
	_tick_clock(delta)


func _switch_human(from_baller) -> void:
	var best = null
	var best_d := INF
	for b in team_ballers[from_baller.team]:
		if b == from_baller or b.controller is HumanInput:
			continue
		var d: float = b.pos.distance_to(ball.pos)
		if d < best_d:
			best_d = d
			best = b
	if best == null:
		return
	var human = from_baller.controller
	from_baller.controller = from_baller.ai_controller
	best.controller = human


func _tick_clock(delta: float) -> void:
	if state.phase == MatchState.Phase.OVERTIME:
		return  # sudden death is untimed: next bucket wins
	if settings.shot_clock_enabled and ball.holder != null:
		state.shot_clock -= delta
		if state.shot_clock <= 0.0:
			EventBus.announce.emit("SHOT CLOCK!", 1)
			_inbound(1 - state.possession)
	state.clock -= delta
	if state.clock <= 0.0:
		state.clock = 0.0
		if ball.state == GameBall.State.SHOT or _dunk_in_progress():
			return  # respect the shot — the buzzer waits for the ball
		_end_quarter()


func _dunk_in_progress() -> bool:
	for b in all_ballers:
		if b.state == Baller.State.DUNK:
			return true
	return false


func _end_quarter() -> void:
	if state.quarter >= settings.quarter_count:
		if state.scores[0] == state.scores[1]:
			state.phase = MatchState.Phase.OVERTIME
			EventBus.overtime_started.emit()
			EventBus.announce.emit("OVERTIME! NEXT BUCKET WINS!", 2)
			AudioManager.play("buzzer", -4.0)
			_reset_formation(rng.randi() % 2, true)
		else:
			_end_match()
	else:
		state.phase = MatchState.Phase.QUARTER_BREAK
		_break_t = 2.2
		AudioManager.play("buzzer", -4.0)
		hud.show_banner("QUARTER %d" % (state.quarter + 1))


func _begin_quarter() -> void:
	state.quarter += 1
	state.clock = settings.quarter_length_sec
	state.shot_clock = settings.shot_clock_sec
	state.phase = MatchState.Phase.PLAY
	hud.hide_banner()
	_reset_formation((state.quarter + 1) % 2)  # possession alternates by quarter
	EventBus.quarter_started.emit(state.quarter)


func _end_match() -> void:
	state.phase = MatchState.Phase.ENDED
	var winner := state.leader()
	var winner_has_human := false
	for b in team_ballers[winner]:
		if b.is_human():
			winner_has_human = true
	# the sim loop is halted now, so posing the winners directly is safe
	for b in team_ballers[winner]:
		if b.state != Baller.State.HURT:
			b.state = Baller.State.CELEBRATE
	# career record only counts when all humans were on one side
	var human_teams := {}
	for t in 2:
		for b in team_ballers[t]:
			if b.is_human():
				human_teams[t] = true
	if human_teams.size() == 1:
		Game.record_result(human_teams.has(winner))
	EventBus.match_ended.emit(winner, winner_has_human)
	hud.show_end_panel(winner)


# ----------------------------------------------------- called by sim actors
func teammates_of(team: int) -> Array:
	return team_ballers[team]


func opponents_of(team: int) -> Array:
	return team_ballers[1 - team]


func nearest_opponent_distance(baller) -> float:
	var best := INF
	for o in team_ballers[1 - baller.team]:
		best = minf(best, o.pos.distance_to(baller.pos))
	return best


func on_possession(baller) -> void:
	if state == null:
		return
	if _auto_switch_from != null and baller.team != _auto_switch_from.team:
		_auto_switch_from = null
	if baller.team != state.possession:
		state.possession = baller.team
		state.shot_clock = settings.shot_clock_sec


func request_shot(shooter, quality: float) -> void:
	var result := ShotResolver.resolve(shooter, quality, self)
	EventBus.shot_taken.emit(shooter)
	if result.blocked:
		var away_from_hoop := Vector2(
			-signf(CourtGeometry.hoop_pos(shooter.team).x),
			rng.randf_range(-0.6, 0.6))
		ball.poke_loose(away_from_hoop.normalized())
		EventBus.shot_blocked.emit(result.blocker, shooter)
	else:
		ball.launch_shot(shooter, result)


func request_pass(passer, intent: PlayerIntent) -> void:
	var target = intent.pass_target
	if target == null:
		target = _pick_pass_target(passer, intent.move)
	if target == null:
		return
	if settings.auto_switch_on_pass and passer.controller is HumanInput:
		_auto_switch_from = passer
	ball.launch_pass(passer, target)
	AudioManager.play("pass", -12.0)


func on_pass_caught(receiver) -> void:
	# control follows the ball: the passing human takes over the receiver
	if (
		_auto_switch_from != null
		and receiver.team == _auto_switch_from.team
		and _auto_switch_from.controller is HumanInput
		and not (receiver.controller is HumanInput)
	):
		var human = _auto_switch_from.controller
		_auto_switch_from.controller = _auto_switch_from.ai_controller
		receiver.controller = human
	_auto_switch_from = null
	# ALLEY-OOP: a long feed to someone standing in dunk range under the rim
	# turns straight into a slam
	if (
		(receiver.state == Baller.State.IDLE or receiver.state == Baller.State.RUN)
		and receiver._dunk_available()
		and ball.pass_origin.distance_to(receiver.pos) > 240.0
	):
		receiver._start_dunk()
		EventBus.announce.emit("ALLEY-OOP!", 2)
		AudioManager.play("whoosh", -8.0)


func _pick_pass_target(passer, aim: Vector2):
	var best = null
	var best_score := -INF
	for tm in team_ballers[passer.team]:
		if tm == passer or tm.state == Baller.State.HURT:
			continue
		var to_tm: Vector2 = tm.pos - passer.pos
		var score: float = -to_tm.length() * 0.002
		if aim.length() > 0.3:
			score += aim.normalized().dot(to_tm.normalized()) * 2.0
		if score > best_score:
			best_score = score
			best = tm
	return best


func complete_dunk(dunker) -> void:
	score_basket(dunker.team, 2, dunker, true)


func score_basket(team: int, points: int, scorer, was_dunk: bool) -> void:
	if state.phase == MatchState.Phase.ENDED:
		return
	var fire_ev: Dictionary = state.register_basket(team, points, scorer, was_dunk)
	hoops[team].flash()
	_spawn_points_popup(points, CourtGeometry.hoop_pos(team))
	EventBus.basket_scored.emit(team, points, scorer, was_dunk)
	EventBus.score_changed.emit(state.scores)
	if state.phase == MatchState.Phase.PLAY and state.clock <= 0.01:
		EventBus.announce.emit("AT THE BUZZER!", 2)
	if was_dunk:
		EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.DUNK, rng), 2)
		cam.add_shake(14.0)
		_rumble(scorer, 0.4, 0.7, 0.3)
		_hitstop(0.09)
	elif points == 3:
		EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.THREE, rng), 1)
	elif rng.randf() < 0.35:
		EventBus.announce.emit(AnnouncerLines.pick(AnnouncerLines.GENERIC, rng), 0)
	for b in fire_ev.heating:
		EventBus.announce.emit(
			"%s IS HEATING UP!" % b.char_def.display_name.to_upper(), 1)
	for b in fire_ev.ignite:
		b.on_fire = true
		EventBus.fire_changed.emit(b, true)
		EventBus.announce.emit(
			"%s IS ON FIRE!" % b.char_def.display_name.to_upper(), 2)
		cam.add_shake(6.0)
		_rumble(b, 0.2, 0.4, 0.5)
	for b in fire_ev.douse:
		b.on_fire = false
		EventBus.fire_changed.emit(b, false)
	scorer.celebrate()
	if state.phase == MatchState.Phase.OVERTIME:
		_end_match()
		return
	_inbound(1 - team)


func _spawn_points_popup(points: int, hoop: Vector2) -> void:
	## Floating "+2"/"+3" in world space above the scored-on rim.
	var l := Label.new()
	l.text = "+%d" % points
	l.add_theme_font_size_override("font_size", 44 if points == 3 else 34)
	l.add_theme_color_override(
		"font_color",
		Color(1.0, 0.85, 0.3) if points == 3 else Color.WHITE)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.05, 0.15))
	l.add_theme_constant_override("outline_size", 8)
	l.position = CourtGeometry.project(hoop) + Vector2(-26.0, -370.0)
	l.z_index = 50
	add_child(l)
	var tw := l.create_tween()
	tw.tween_property(l, "position:y", l.position.y - 70.0, 0.7)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.7)
	tw.tween_callback(l.queue_free)


func _inbound(team: int) -> void:
	## NBA Jam style: no stoppage — the scored-on team gets it under their
	## own basket and play rolls on.
	var inbound_spot := CourtGeometry.hoop_pos(1 - team)
	var best = null
	var best_d := INF
	for b in team_ballers[team]:
		if b.state == Baller.State.HURT:
			continue
		var d: float = b.pos.distance_to(inbound_spot)
		if d < best_d:
			best_d = d
			best = b
	if best == null:
		best = team_ballers[team][0]
	ball.give_to(best)


# ------------------------------------------------------------------- pause
func _poll_pause() -> void:
	var pressed := Input.is_action_just_pressed("ui_pause")
	for h in humans:
		var dev: int = h.device
		if dev == -2:  # solo merged seat: keyboard handled above, pad 0 here
			var pads := Input.get_connected_joypads()
			dev = pads[0] if not pads.is_empty() else -1
		if dev >= 0:
			var cur := Input.is_joy_button_pressed(dev, JOY_BUTTON_START)
			if cur and not _pause_prev.get(dev, false):
				pressed = true
			_pause_prev[dev] = cur
	if pressed:
		get_tree().paused = true
		hud.show_pause()
