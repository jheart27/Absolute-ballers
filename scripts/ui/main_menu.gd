class_name MainMenu
extends Control
## Title screen + match settings (team size, quarter length, difficulty,
## fire mode, shot clock). Settings write straight into Game.settings and
## persist to user://settings.cfg.

const TEAM_SIZES: Array = [1, 2, 3, 5]
const QUARTER_LENGTHS: Array = [60.0, 120.0, 180.0]
const DIFF_NAMES: Array = ["ROOKIE", "ARCADE", "LEGEND"]

var _size_btn: Button
var _quarter_btn: Button
var _diff_btn: Button
var _fire_btn: Button
var _clock_btn: Button


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.09, 0.06, 0.16)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_child(v)

	var title := Label.new()
	title.text = "ABSOLUTE BALLERS"
	title.add_theme_font_size_override("font_size", 64)
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	title.add_theme_color_override("font_outline_color", Color(0.5, 0.15, 0.35))
	title.add_theme_constant_override("outline_size", 10)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	var sub := Label.new()
	sub.text = "arcade hoops — she's on fire"
	sub.add_theme_font_size_override("font_size", 20)
	sub.add_theme_color_override("font_color", Color(0.8, 0.7, 0.95))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	v.add_child(_spacer(18.0))

	var play := _button(v, "EXHIBITION", func() -> void:
		Game.goto_team_select("exhibition"))
	_button(v, "TOURNAMENT", func() -> void: Game.goto_team_select("tournament"))
	v.add_child(_spacer(12.0))
	_size_btn = _button(v, "", _cycle_team_size)
	_quarter_btn = _button(v, "", _cycle_quarter)
	_diff_btn = _button(v, "", _cycle_difficulty)
	_fire_btn = _button(v, "", _cycle_fire)
	_clock_btn = _button(v, "", _cycle_shot_clock)
	v.add_child(_spacer(12.0))
	_button(v, "QUIT", func() -> void: get_tree().quit())
	_refresh()
	play.grab_focus()


func _refresh() -> void:
	var s: MatchSettings = Game.settings
	_size_btn.text = "TEAM SIZE: %dv%d" % [s.team_size, s.team_size]
	_quarter_btn.text = "QUARTERS: %d x %d:%02d" % [
		s.quarter_count, int(s.quarter_length_sec / 60.0),
		int(s.quarter_length_sec) % 60]
	_diff_btn.text = "DIFFICULTY: %s" % DIFF_NAMES[s.difficulty]
	_fire_btn.text = "ON FIRE: %s" % (
		"PER PLAYER" if s.fire_mode == MatchSettings.FireMode.PER_PLAYER
		else "PER TEAM")
	_clock_btn.text = "SHOT CLOCK: %s" % ("ON" if s.shot_clock_enabled else "OFF")


func _cycle_team_size() -> void:
	var i := TEAM_SIZES.find(Game.settings.team_size)
	Game.settings.team_size = TEAM_SIZES[(i + 1) % TEAM_SIZES.size()]
	_apply()


func _cycle_quarter() -> void:
	var i := QUARTER_LENGTHS.find(Game.settings.quarter_length_sec)
	Game.settings.quarter_length_sec = QUARTER_LENGTHS[(i + 1) % QUARTER_LENGTHS.size()]
	_apply()


func _cycle_difficulty() -> void:
	Game.settings.difficulty = (Game.settings.difficulty + 1) % 3
	_apply()


func _cycle_fire() -> void:
	Game.settings.fire_mode = (
		MatchSettings.FireMode.PER_TEAM
		if Game.settings.fire_mode == MatchSettings.FireMode.PER_PLAYER
		else MatchSettings.FireMode.PER_PLAYER)
	_apply()


func _cycle_shot_clock() -> void:
	Game.settings.shot_clock_enabled = not Game.settings.shot_clock_enabled
	_apply()


func _apply() -> void:
	Game.save_settings()
	_refresh()


func _button(parent: Control, text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(340.0, 44.0)
	b.add_theme_font_size_override("font_size", 21)
	b.pressed.connect(callback)
	parent.add_child(b)
	return b


func _spacer(h: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0.0, h)
	return c
