class_name TournamentScreen
extends Control
## Bracket display between tournament matches. Reads Game.tournament.

func _ready() -> void:
	var t: TournamentState = Game.tournament
	if t == null:
		Game.goto_main_menu()
		return
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.09, 0.06, 0.16)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.add_theme_constant_override("separation", 14)
	add_child(v)

	var heading := "TOURNAMENT — %s" % t.round_name()
	if t.champion >= 0:
		heading = "TOURNAMENT COMPLETE"
	var title := _label(heading, 40, Color(1.0, 0.85, 0.3))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(title)

	var row := HBoxContainer.new()
	row.size_flags_vertical = Control.SIZE_EXPAND_FILL
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 40)
	v.add_child(row)
	var round_titles: Array = ["QUARTERFINALS", "SEMIFINALS", "FINAL"]
	for r in 3:
		var col := VBoxContainer.new()
		col.add_theme_constant_override("separation", 10)
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		row.add_child(col)
		col.add_child(_label(round_titles[r], 20, Color(0.7, 0.65, 0.9)))
		if r < t.rounds.size():
			var alive: Array = t.rounds[r]
			for p in range(0, alive.size(), 2):
				if p + 1 < alive.size():
					col.add_child(_pair_label(t, r, alive[p], alive[p + 1]))
		else:
			col.add_child(_label("TBD", 18, Color(0.45, 0.45, 0.6)))
	var champ_col := VBoxContainer.new()
	champ_col.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(champ_col)
	champ_col.add_child(_label("CHAMPION", 20, Color(0.7, 0.65, 0.9)))
	if t.champion >= 0:
		var td: TeamDef = t.entries[t.champion].team_def
		champ_col.add_child(_label(td.team_name.to_upper(), 26, td.primary_color))
	else:
		champ_col.add_child(_label("?", 26, Color(0.45, 0.45, 0.6)))

	var footer := VBoxContainer.new()
	footer.alignment = BoxContainer.ALIGNMENT_CENTER
	footer.add_theme_constant_override("separation", 10)
	v.add_child(footer)
	if t.champion >= 0:
		var msg := (
			"YOUR SQUAD TAKES THE CROWN! ABSOLUTE BALLERS, ALL OF YOU!"
			if t.entries[t.champion].is_player
			else "ELIMINATED — THE CROWN GOES ELSEWHERE.")
		footer.add_child(_center_label(msg, 24, Color.WHITE))
		footer.add_child(_button("BACK TO MENU", func() -> void: Game.goto_main_menu()))
	else:
		var play := _button("PLAY %s" % t.round_name(), func() -> void:
			Game.start_match(t.build_player_match_config(Game.settings)))
		footer.add_child(play)
		footer.add_child(_button("ABANDON TOURNAMENT", func() -> void:
			Game.goto_main_menu()))
		play.grab_focus()


func _pair_label(t: TournamentState, r: int, a: int, b: int) -> Label:
	var winner := -1
	if r < t.winners_by_round.size():
		var winners: Array = t.winners_by_round[r]
		winner = a if winners.has(a) else (b if winners.has(b) else -1)
	var l := _label("%s vs %s" % [_entry_name(t, a), _entry_name(t, b)], 18,
		Color(0.9, 0.88, 1.0))
	if winner >= 0:
		l.text += "  -> %s" % _entry_name(t, winner)
		l.add_theme_color_override("font_color", Color(0.6, 0.9, 0.6))
	if t.entries[a].is_player or t.entries[b].is_player:
		l.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	return l


func _entry_name(t: TournamentState, i: int) -> String:
	var short: String = t.entries[i].team_def.short_name
	return "%s%s" % [short, "(YOU)" if t.entries[i].is_player else ""]


func _label(text: String, font_size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	return l


func _center_label(text: String, font_size: int, color: Color) -> Label:
	var l := _label(text, font_size, color)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l


func _button(text: String, callback: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(300.0, 46.0)
	b.add_theme_font_size_override("font_size", 22)
	b.pressed.connect(callback)
	return b
