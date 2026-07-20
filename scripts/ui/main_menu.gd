class_name MainMenu
extends Control
## Title screen. Four items per the design: SINGLE PLAYER, VERSUS, OPTIONS,
## QUIT. Match settings + demo + how-to-play live under OPTIONS so the front
## page stays clean while we focus on single player.

const HELP_LINES: Array = [
	["MOVE", "WASD / arrows / left stick"],
	["SHOOT  &  BLOCK", "K or Space  /  A     (release at the top of the jump!)"],
	["PASS  &  STEAL", "J  /  B     (hold TURBO while stealing to SHOVE)"],
	["TURBO", "L or Shift  /  X or right trigger"],
	["SWITCH baller", "I  /  Y"],
	["PAUSE", "Esc or P  /  Start"],
	["", ""],
	["DUNK", "hold SHOOT near the rim — dunks always drop"],
	["ALLEY-OOP", "long pass to a teammate under the basket"],
	["ON FIRE", "score 3 in a row — boosted until they answer"],
	["GOALTEND", "legal! jump and swat shots out of the air"],
]

var _panel: Control  # the active submenu overlay, or null
var _root_col: CenterContainer  # the main list, hidden while a panel is open


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.09, 0.06, 0.16)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_build_root()


func _build_root() -> void:
	var v := _menu_column()
	var title := Label.new()
	title.text = "ABSOLUTE BALLERS"
	title.add_theme_font_size_override("font_size", 64)
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	title.add_theme_color_override("font_outline_color", Color(0.5, 0.15, 0.35))
	title.add_theme_constant_override("outline_size", 10)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := _text("arcade hoops — she's on fire", 20, Color(0.8, 0.7, 0.95))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	if Game.record_wins + Game.record_losses > 0:
		var rec := _text("CAREER: %d W — %d L" % [Game.record_wins, Game.record_losses],
			17, Color(0.65, 0.85, 0.7))
		rec.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		v.add_child(rec)
	v.add_child(_spacer(20.0))
	var first := _button(v, "SINGLE PLAYER", _open_single_player)
	_button(v, "VERSUS", _open_versus)
	_button(v, "OPTIONS", _open_options)
	_button(v, "QUIT", func() -> void: get_tree().quit())
	first.grab_focus()


# --------------------------------------------------------------- SINGLE PLAYER
func _open_single_player() -> void:
	var v := _open_panel("SINGLE PLAYER")
	_button(v, "QUICK MATCH", func() -> void: _start_solo("exhibition"))
	_button(v, "TOURNAMENT", func() -> void: _start_solo("tournament"))
	_back_button(v)


func _start_solo(context: String) -> void:
	## Auto-seat one human (keyboard + pad both work via SOLO_DEVICE) on team 0
	## and jump straight in — no lobby needed for single player.
	var chars: Array = Game.character_list()
	var n: int = Game.settings.team_size
	var seat := {
		"device": HumanInput.SOLO_DEVICE, "seat": 0, "team": 0, "char_index": 0}
	if context == "tournament":
		var entry := {
			"team_def": Game.teams[0],
			"roster": chars.slice(0, n),
			"human_seats": [seat],
			"is_player": true,
		}
		var ts := TournamentState.new()
		ts.build(entry, Game.teams, chars, n)
		Game.tournament = ts
		Game.goto_tournament_screen()
		return
	var c := MatchConfig.new()
	c.settings = Game.settings
	c.context = "exhibition"
	c.team_defs = [Game.teams[0], Game.teams[1]]
	c.rosters = [chars.slice(0, n), chars.slice(n, n * 2)]
	c.human_seats = [seat]
	c.ai_levels = [Game.settings.difficulty, Game.settings.difficulty]
	Game.start_match(c)


func _open_versus() -> void:
	Game.goto_team_select("exhibition")


# --------------------------------------------------------------------- OPTIONS
func _open_options() -> void:
	var v := _open_panel("OPTIONS")
	var s: MatchSettings = Game.settings
	_cycle_button(v, "TEAM SIZE", func() -> String:
		return "%dv%d" % [s.team_size, s.team_size], func() -> void:
			var sizes := [1, 2, 3, 5]
			s.team_size = sizes[(sizes.find(s.team_size) + 1) % sizes.size()])
	_cycle_button(v, "QUARTER LENGTH", func() -> String:
		return "%d:%02d" % [int(s.quarter_length_sec / 60), int(s.quarter_length_sec) % 60],
		func() -> void:
			var q := [60.0, 120.0, 180.0]
			s.quarter_length_sec = q[(q.find(s.quarter_length_sec) + 1) % q.size()])
	_cycle_button(v, "DIFFICULTY", func() -> String:
		return ["ROOKIE", "ARCADE", "LEGEND"][s.difficulty], func() -> void:
			s.difficulty = (s.difficulty + 1) % 3)
	_cycle_button(v, "ON FIRE", func() -> String:
		return "PER PLAYER" if s.fire_mode == MatchSettings.FireMode.PER_PLAYER \
			else "PER TEAM", func() -> void:
			s.fire_mode = (MatchSettings.FireMode.PER_TEAM
				if s.fire_mode == MatchSettings.FireMode.PER_PLAYER
				else MatchSettings.FireMode.PER_PLAYER))
	_cycle_button(v, "SHOT CLOCK", func() -> String:
		return "ON" if s.shot_clock_enabled else "OFF", func() -> void:
			s.shot_clock_enabled = not s.shot_clock_enabled)
	_cycle_button(v, "CONTROL HINTS", func() -> String:
		return "ON" if s.show_control_hints else "OFF", func() -> void:
			s.show_control_hints = not s.show_control_hints)
	v.add_child(_spacer(10.0))
	_button(v, "HOW TO PLAY", _open_help)
	_button(v, "WATCH DEMO", func() -> void:
		Game.start_match(MatchConfig.quick_default(
			Game.settings, Game.teams, Game.character_list())))
	_back_button(v)


# ------------------------------------------------------------------- HOW TO PLAY
func _open_help() -> void:
	# solid, high-contrast full-screen page (previous version was see-through)
	var page := _open_panel("HOW TO PLAY", 0.98)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 26)
	grid.add_theme_constant_override("v_separation", 8)
	page.add_child(grid)
	for pair in HELP_LINES:
		var label := _text(pair[0], 20, Color(1.0, 0.82, 0.3))
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		label.custom_minimum_size = Vector2(220.0, 0.0)
		grid.add_child(label)
		grid.add_child(_text(pair[1], 20, Color(0.95, 0.95, 1.0)))
	page.add_child(_spacer(14.0))
	_back_button(page)


# ----------------------------------------------------------------- panel utils
func _menu_column() -> VBoxContainer:
	_root_col = CenterContainer.new()
	_root_col.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_root_col)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	_root_col.add_child(v)
	return v


func _open_panel(heading: String, dim_alpha := 1.0) -> VBoxContainer:
	if _panel != null and is_instance_valid(_panel):
		_panel.queue_free()
	_root_col.visible = false  # hide the main list so nothing shows through
	_panel = Control.new()
	_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_panel)
	var dim := ColorRect.new()
	dim.color = Color(0.07, 0.04, 0.13, dim_alpha)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_panel.add_child(center)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_child(v)
	var title := _text(heading, 40, Color(1.0, 0.85, 0.3))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	v.add_child(_spacer(8.0))
	return v


func _back_button(v: VBoxContainer) -> void:
	var b := _button(v, "BACK", func() -> void:
		Game.save_settings()
		_panel.queue_free()
		_panel = null
		_root_col.visible = true)
	b.grab_focus()


func _cycle_button(v: Control, label: String, value: Callable, act: Callable) -> void:
	var b := Button.new()
	b.custom_minimum_size = Vector2(400.0, 44.0)
	b.add_theme_font_size_override("font_size", 21)
	b.text = "%s:  %s" % [label, value.call()]
	b.pressed.connect(func() -> void:
		AudioManager.play("click", -8.0)
		act.call()
		b.text = "%s:  %s" % [label, value.call()])
	v.add_child(b)


func _button(parent: Control, text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(340.0, 44.0)
	b.add_theme_font_size_override("font_size", 21)
	b.pressed.connect(func() -> void: AudioManager.play("click", -8.0))
	b.pressed.connect(callback)
	parent.add_child(b)
	return b


func _text(s: String, font_size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = s
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	return l


func _spacer(h: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0.0, h)
	return c
