class_name TeamSelect
extends Control
## Couch lobby: up to 4 humans (keyboard + gamepads) press SHOOT to join a
## seat, pick a side and a baller, and lock in. Unfilled roster slots are
## auto-filled with AI ballers. In tournament context all humans join the
## home squad and the away side belongs to the bracket.
##
## Per-device controls in the lobby:
##   SHOOT/A joins & locks - PASS/B unlocks or leaves - stick/dpad left-right
##   picks a side - up/down cycles baller - START (Enter) begins the match.

var context := "exhibition"

var seats: Array = []  # {device:int, side:int, char_i:int, locked:bool}
var franchise: Array = [1, 2]  # indices into Game.teams

var _poller := DevicePoller.new()
var _pool: Array = []
var _dirty := true
var _side_seat_boxes: Array = []
var _side_ai_boxes: Array = []
var _franchise_btns: Array = []
var _status_label: Label


func _ready() -> void:
	_pool = Game.character_list()
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.09, 0.06, 0.16)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 8)
	add_child(v)

	var title := _label("SQUAD SELECT" if context == "exhibition"
		else "TOURNAMENT — BUILD YOUR SQUAD", 40, Color(1.0, 0.85, 0.3))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)

	var row := HBoxContainer.new()
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.add_theme_constant_override("separation", 20)
	v.add_child(row)
	for side in 2:
		var panel := PanelContainer.new()
		panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(panel)
		var pv := VBoxContainer.new()
		pv.add_theme_constant_override("separation", 6)
		panel.add_child(pv)
		var fbtn := Button.new()
		fbtn.add_theme_font_size_override("font_size", 24)
		var side_i := side
		fbtn.pressed.connect(func() -> void: _cycle_franchise(side_i))
		pv.add_child(fbtn)
		_franchise_btns.append(fbtn)
		var seat_box := VBoxContainer.new()
		pv.add_child(seat_box)
		_side_seat_boxes.append(seat_box)
		var ai_box := VBoxContainer.new()
		pv.add_child(ai_box)
		_side_ai_boxes.append(ai_box)

	_status_label = _label("", 20, Color(0.85, 0.8, 1.0))
	_status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(_status_label)
	var help := _label(
		"SHOOT (A / K·Space) join + lock  |  PASS (B / J) unlock / leave  |  "
		+ "left-right pick side  |  up-down pick baller  |  START (Enter) play",
		16, Color(0.6, 0.55, 0.8))
	help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(help)
	var back := Button.new()
	back.text = "BACK"
	back.custom_minimum_size = Vector2(160.0, 40.0)
	back.pressed.connect(func() -> void: Game.goto_main_menu())
	v.add_child(back)


func _process(_delta: float) -> void:
	_poll_lobby()
	if _dirty:
		_dirty = false
		_refresh()


# ------------------------------------------------------------------ polling
func _devices() -> Array:
	var out: Array = [-1]
	out.append_array(Input.get_connected_joypads())
	return out


func _seat_of(device: int):
	for s in seats:
		if s.device == device:
			return s
	return null


func _humans_on(side: int) -> int:
	var n := 0
	for s in seats:
		if s.side == side:
			n += 1
	return n


func _poll_lobby() -> void:
	for device in _devices():
		var seat = _seat_of(device)
		if seat == null:
			if _poller.just(device, "a") and seats.size() < 4:
				_join(device)
			continue
		if _poller.just(device, "a"):
			seat.locked = true
			_dirty = true
		elif _poller.just(device, "b"):
			if seat.locked:
				seat.locked = false
			else:
				seats.erase(seat)
			_dirty = true
		elif not seat.locked:
			if context == "exhibition":
				if _poller.just(device, "left") and seat.side == 1 \
						and _humans_on(0) < Game.settings.team_size:
					seat.side = 0
					_dirty = true
				elif _poller.just(device, "right") and seat.side == 0 \
						and _humans_on(1) < Game.settings.team_size:
					seat.side = 1
					_dirty = true
			if _poller.just(device, "down"):
				seat.char_i = _next_free_char(seat, 1)
				_dirty = true
			elif _poller.just(device, "up"):
				seat.char_i = _next_free_char(seat, -1)
				_dirty = true
		if _poller.just(device, "start") and _ready_to_start():
			_start()
			return


func _join(device: int) -> void:
	var side := 0
	if context == "exhibition" and _humans_on(1) < _humans_on(0) \
			and _humans_on(1) < Game.settings.team_size:
		side = 1
	if _humans_on(side) >= Game.settings.team_size:
		side = 1 - side
		if context == "tournament" or _humans_on(side) >= Game.settings.team_size:
			return  # lobby full for this mode
	var seat := {"device": device, "side": side, "char_i": -1, "locked": false}
	seats.append(seat)
	seat.char_i = _next_free_char(seat, 1)
	_dirty = true


func _next_free_char(seat: Dictionary, dir: int) -> int:
	var i: int = seat.char_i
	for _step in _pool.size():
		i = wrapi(i + dir, 0, _pool.size())
		var taken := false
		for s in seats:
			if s != seat and s.char_i == i:
				taken = true
		if not taken:
			return i
	return maxi(seat.char_i, 0)


func _ready_to_start() -> bool:
	if seats.is_empty():
		return false
	for s in seats:
		if not s.locked:
			return false
	return true


# ------------------------------------------------------------------ display
func _cycle_franchise(side: int) -> void:
	var n: int = Game.teams.size()
	franchise[side] = wrapi(franchise[side] + 1, 0, n)
	if franchise[side] == franchise[1 - side]:
		franchise[side] = wrapi(franchise[side] + 1, 0, n)
	_dirty = true


func _refresh() -> void:
	var rosters := _planned_rosters()
	for side in 2:
		var team_def: TeamDef = Game.teams[franchise[side]]
		var btn: Button = _franchise_btns[side]
		if context == "tournament" and side == 1:
			btn.text = "BRACKET OPPONENTS"
			btn.disabled = true
			btn.modulate = Color(0.7, 0.7, 0.8)
		else:
			btn.text = "< %s >" % team_def.team_name.to_upper()
			btn.modulate = team_def.primary_color
		for box in [_side_seat_boxes[side], _side_ai_boxes[side]]:
			for child in box.get_children():
				child.queue_free()
		for s in seats:
			if s.side != side:
				continue
			var seat_num := seats.find(s)
			var cd: CharacterDef = _pool[s.char_i]
			var text := "P%d  %s — %s%s" % [
				seat_num + 1, cd.display_name, cd.tagline,
				"  [LOCKED]" if s.locked else ""]
			var l := _label(text, 20, HumanInput.SEAT_COLORS[seat_num % 4])
			_side_seat_boxes[side].add_child(l)
		if not (context == "tournament" and side == 1):
			var human_count := _humans_on(side)
			for i in range(human_count, rosters[side].size()):
				var cd: CharacterDef = rosters[side][i]
				_side_ai_boxes[side].add_child(
					_label("AI  %s" % cd.display_name, 18, Color(0.6, 0.6, 0.75)))
	_status_label.text = (
		"ALL LOCKED — PRESS START!" if _ready_to_start()
		else "waiting for ballers to lock in... (%d joined)" % seats.size())


func _planned_rosters() -> Array:
	## Human picks first (in seat order), AI fills the rest, no duplicates.
	var taken := {}
	for s in seats:
		taken[_pool[s.char_i].id] = true
	var rosters: Array = [[], []]
	var n: int = Game.settings.team_size
	for side in 2:
		for s in seats:
			if s.side == side:
				rosters[side].append(_pool[s.char_i])
	for side in 2:
		for cd in _pool:
			if rosters[side].size() >= n:
				break
			if not taken.has(cd.id):
				rosters[side].append(cd)
				taken[cd.id] = true
	return rosters


# -------------------------------------------------------------------- start
func _start() -> void:
	var rosters := _planned_rosters()
	var human_seats: Array = []
	var per_side_index: Array = [0, 0]
	for seat_num in seats.size():
		var s: Dictionary = seats[seat_num]
		human_seats.append({
			"device": s.device,
			"seat": seat_num,
			"team": s.side,
			"char_index": per_side_index[s.side],
		})
		per_side_index[s.side] += 1
	if context == "tournament":
		var entry := {
			"team_def": Game.teams[franchise[0]],
			"roster": rosters[0],
			"human_seats": human_seats,
			"is_player": true,
		}
		var ts := TournamentState.new()
		ts.build(entry, Game.teams, _pool, Game.settings.team_size)
		Game.tournament = ts
		Game.goto_tournament_screen()
		return
	var c := MatchConfig.new()
	c.settings = Game.settings
	c.context = "exhibition"
	c.team_defs = [Game.teams[franchise[0]], Game.teams[franchise[1]]]
	c.rosters = rosters
	c.human_seats = human_seats
	c.ai_levels = [Game.settings.difficulty, Game.settings.difficulty]
	Game.start_match(c)


func _label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l
