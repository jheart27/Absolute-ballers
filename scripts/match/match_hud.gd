class_name MatchHUD
extends CanvasLayer
## Score/clock strip, announcer popups, quarter banners, pause menu, and the
## end-of-match panel. Listens to EventBus; reads (never writes) match state.

const POPUP_COLORS: Array = [
	Color.WHITE, Color(1.0, 0.9, 0.3), Color(1.0, 0.45, 0.15)]

var match_scene = null

var _score_labels: Array = []
var _clock_label: Label
var _shot_clock_label: Label
var _banner: Label
var _popup_stack := 0
var _pause_panel: Control
var _resume_btn: Button
var _end_panel: Control
var _root: Control


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS  # pause menu must keep working
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_build_score_strip()
	_banner = _make_label("", 72, Color(1.0, 0.85, 0.3))
	_banner.set_anchors_preset(Control.PRESET_FULL_RECT)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_banner.visible = false
	_root.add_child(_banner)
	_build_pause_panel()
	EventBus.announce.connect(_on_announce)


func _exit_tree() -> void:
	EventBus.announce.disconnect(_on_announce)


func _build_score_strip() -> void:
	var strip := HBoxContainer.new()
	strip.set_anchors_preset(Control.PRESET_CENTER_TOP)
	strip.anchor_left = 0.5
	strip.anchor_right = 0.5
	strip.offset_top = 10.0
	strip.grow_horizontal = Control.GROW_DIRECTION_BOTH
	strip.add_theme_constant_override("separation", 26)
	strip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(strip)
	for t in 2:
		var team_def: TeamDef = match_scene.config.team_defs[t]
		var l := _make_label("%s 0" % team_def.short_name, 30, team_def.primary_color)
		_score_labels.append(l)
	_clock_label = _make_label("Q1 0:00", 30, Color.WHITE)
	_shot_clock_label = _make_label("", 22, Color(1.0, 0.6, 0.4))
	strip.add_child(_score_labels[0])
	strip.add_child(_clock_label)
	strip.add_child(_shot_clock_label)
	strip.add_child(_score_labels[1])


func _process(_delta: float) -> void:
	if match_scene == null or match_scene.state == null:
		return
	var st = match_scene.state
	for t in 2:
		var team_def: TeamDef = match_scene.config.team_defs[t]
		_score_labels[t].text = "%s %d" % [team_def.short_name, st.scores[t]]
		var burning := false
		for b in match_scene.team_ballers[t]:
			if b.on_fire:
				burning = true
		_score_labels[t].add_theme_color_override(
			"font_color",
			Color(1.0, 0.5, 0.1) if burning else team_def.primary_color)
	if st.phase == MatchState.Phase.OVERTIME:
		_clock_label.text = "OT"
	else:
		_clock_label.text = "Q%d %s" % [st.quarter, _fmt_clock(st.clock)]
	_shot_clock_label.text = (
		str(maxi(0, int(ceil(st.shot_clock)))) if st.settings.shot_clock_enabled else "")


static func _fmt_clock(t: float) -> String:
	var s := maxi(0, int(ceil(t)))
	return "%d:%02d" % [int(s / 60.0), s % 60]


# ---------------------------------------------------------------- announcer
func _on_announce(text: String, tier: int) -> void:
	var l := _make_label(text, 34 + tier * 14, POPUP_COLORS[clampi(tier, 0, 2)])
	l.anchor_left = 0.0
	l.anchor_right = 1.0
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.position = Vector2(0.0, 120.0 + _popup_stack * 56.0)
	l.pivot_offset = Vector2(get_viewport().get_visible_rect().size.x * 0.5, 24.0)
	_popup_stack = (_popup_stack + 1) % 3
	_root.add_child(l)
	l.scale = Vector2(1.6, 1.6)
	var tw := l.create_tween()
	tw.tween_property(l, "scale", Vector2.ONE, 0.16) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_interval(1.0)
	tw.tween_property(l, "modulate:a", 0.0, 0.4)
	tw.tween_callback(l.queue_free)


func show_banner(text: String) -> void:
	_banner.text = text
	_banner.visible = true


func hide_banner() -> void:
	_banner.visible = false


# -------------------------------------------------------------- pause / end
func _build_pause_panel() -> void:
	_pause_panel = _overlay_panel()
	var v := _panel_vbox(_pause_panel)
	v.add_child(_make_label("PAUSED", 48, Color.WHITE))
	_resume_btn = _make_button("RESUME", _on_resume)
	v.add_child(_resume_btn)
	v.add_child(_make_button("QUIT MATCH", _on_quit))


func show_pause() -> void:
	_pause_panel.visible = true
	_resume_btn.grab_focus()


func _on_resume() -> void:
	get_tree().paused = false
	_pause_panel.visible = false


func _on_quit() -> void:
	get_tree().paused = false
	Game.finish_match(match_scene.state.leader())


func show_end_panel(winner: int) -> void:
	_end_panel = _overlay_panel()
	_end_panel.visible = true
	var v := _panel_vbox(_end_panel)
	var team_def: TeamDef = match_scene.config.team_defs[winner]
	var st = match_scene.state
	v.add_child(_make_label("%s WIN!" % team_def.team_name.to_upper(), 54,
		team_def.primary_color))
	v.add_child(_make_label("%d - %d" % [st.scores[0], st.scores[1]], 40, Color.WHITE))
	var mvp = st.mvp()
	if mvp != null:
		v.add_child(_make_label(
			"MVP: %s (%d PTS)" % [
				mvp.char_def.display_name.to_upper(),
				int(st.player_points.get(mvp, 0))],
			26, Color(1.0, 0.85, 0.3)))
	var btn := _make_button("CONTINUE", func() -> void: Game.finish_match(winner))
	v.add_child(btn)
	btn.grab_focus()


# ----------------------------------------------------------------- helpers
func _overlay_panel() -> Control:
	var p := Control.new()
	p.set_anchors_preset(Control.PRESET_FULL_RECT)
	p.visible = false
	var dim := ColorRect.new()
	dim.color = Color(0.05, 0.03, 0.1, 0.75)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	p.add_child(dim)
	_root.add_child(p)
	return p


func _panel_vbox(panel: Control) -> VBoxContainer:
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.add_child(center)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 16)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	center.add_child(v)
	return v


func _make_label(text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.08, 0.04, 0.14))
	l.add_theme_constant_override("outline_size", 8)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _make_button(text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(260.0, 46.0)
	b.add_theme_font_size_override("font_size", 22)
	b.pressed.connect(callback)
	return b
