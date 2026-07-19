class_name MainMenu
extends Control
## Title screen + match settings (team size, quarter length, difficulty,
## fire mode, shot clock). Settings write straight into Game.settings and
## persist to user://settings.cfg.

const TEAM_SIZES: Array = [1, 2, 3, 5]
const QUARTER_LENGTHS: Array = [60.0, 120.0, 180.0]
const DIFF_NAMES: Array = ["ROOKIE", "ARCADE", "LEGEND"]

const HELP_LINES: Array = [
	"MOVE — WASD / arrows / left stick",
	"SHOOT / BLOCK — K or Space / A button",
	"    (release at the TOP of the jump for a perfect shot)",
	"PASS / STEAL — J / B button  (hold TURBO while stealing to SHOVE)",
	"TURBO — L or Shift / X or right trigger",
	"SWITCH baller — I / Y button      PAUSE — Esc or P / Start",
	"",
	"Near the rim, SHOOT becomes a DUNK — dunks always drop.",
	"Feed a long pass to a cutter under the basket for an ALLEY-OOP.",
	"Score 3 personal buckets in a row to catch FIRE.",
	"Goaltending is legal: jump and swat shots right out of the air.",
]

var _size_btn: Button
var _quarter_btn: Button
var _diff_btn: Button
var _fire_btn: Button
var _clock_btn: Button
var _help: Control = null
var _help_close: Button = null


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
	if Game.record_wins + Game.record_losses > 0:
		var rec := Label.new()
		rec.text = "CAREER: %d W — %d L" % [Game.record_wins, Game.record_losses]
		rec.add_theme_font_size_override("font_size", 17)
		rec.add_theme_color_override("font_color", Color(0.65, 0.85, 0.7))
		rec.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		v.add_child(rec)
	v.add_child(_spacer(18.0))

	var play := _button(v, "EXHIBITION", func() -> void:
		Game.goto_team_select("exhibition"))
	_button(v, "TOURNAMENT", func() -> void: Game.goto_team_select("tournament"))
	_button(v, "WATCH DEMO", func() -> void:
		Game.start_match(MatchConfig.quick_default(
			Game.settings, Game.teams, Game.character_list())))
	_button(v, "HOW TO PLAY", _show_help)
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


func _show_help() -> void:
	if _help != null:
		_help.visible = true
		_help_close.grab_focus()
		return
	_help = Control.new()
	_help.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_help)
	var dim := ColorRect.new()
	dim.color = Color(0.05, 0.03, 0.1, 0.9)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_help.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	_help.add_child(center)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_child(v)
	var title := Label.new()
	title.text = "HOW TO PLAY"
	title.add_theme_font_size_override("font_size", 40)
	title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)
	for line in HELP_LINES:
		var l := Label.new()
		l.text = line
		l.add_theme_font_size_override("font_size", 19)
		l.add_theme_color_override("font_color", Color(0.9, 0.88, 1.0))
		v.add_child(l)
	_help_close = Button.new()
	_help_close.text = "CLOSE"
	_help_close.custom_minimum_size = Vector2(200.0, 42.0)
	_help_close.pressed.connect(func() -> void: _help.visible = false)
	v.add_child(_help_close)
	_help_close.grab_focus()


func _button(parent: Control, text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(340.0, 44.0)
	b.add_theme_font_size_override("font_size", 21)
	b.pressed.connect(func() -> void: AudioManager.play("click", -8.0))
	b.pressed.connect(callback)
	parent.add_child(b)
	return b


func _spacer(h: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0.0, h)
	return c
