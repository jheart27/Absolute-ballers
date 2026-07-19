extends Node
## Autoload "Game": app flow (menu -> team select -> match -> tournament),
## the persistent MatchSettings, the loaded roster, and match handoff.

const SETTINGS_PATH := "user://settings.cfg"

var settings: MatchSettings = MatchSettings.new()
var characters := {}  # id -> CharacterDef
var teams: Array = []  # TeamDef list
var tournament = null  # TournamentState while a bracket is running
var pending_match = null  # MatchConfig consumed by the next MatchScene

var _current_screen: Node = null


func _ready() -> void:
	InputSetup.install()
	characters = Roster.load_characters()
	teams = Roster.load_teams()
	load_settings()


func character_list() -> Array:
	var out: Array = characters.values()
	out.sort_custom(func(a, b): return a.id < b.id)
	return out


# ------------------------------------------------------------------ screens
func goto_main_menu() -> void:
	tournament = null
	_switch(MainMenu.new())


func goto_team_select(context: String) -> void:
	var ts := TeamSelect.new()
	ts.context = context
	_switch(ts)


func goto_tournament_screen() -> void:
	_switch(TournamentScreen.new())


func start_match(config: MatchConfig) -> void:
	pending_match = config
	_switch(MatchScene.new())


func finish_match(winner_team: int) -> void:
	get_tree().paused = false
	var was_tournament: bool = pending_match != null and pending_match.context == "tournament"
	pending_match = null
	if was_tournament and tournament != null:
		tournament.record_player_result(winner_team == 0)
		goto_tournament_screen()
	else:
		goto_main_menu()


func _switch(screen: Node) -> void:
	if _current_screen != null and is_instance_valid(_current_screen):
		_current_screen.queue_free()
	_current_screen = screen
	get_tree().root.add_child.call_deferred(screen)


# ----------------------------------------------------------------- settings
func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("match", "team_size", settings.team_size)
	cfg.set_value("match", "quarter_length_sec", settings.quarter_length_sec)
	cfg.set_value("match", "difficulty", settings.difficulty)
	cfg.set_value("match", "fire_mode", settings.fire_mode)
	cfg.set_value("match", "shot_clock_enabled", settings.shot_clock_enabled)
	cfg.save(SETTINGS_PATH)


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) != OK:
		return
	settings.team_size = cfg.get_value("match", "team_size", settings.team_size)
	settings.quarter_length_sec = cfg.get_value(
		"match", "quarter_length_sec", settings.quarter_length_sec)
	settings.difficulty = cfg.get_value("match", "difficulty", settings.difficulty)
	settings.fire_mode = cfg.get_value("match", "fire_mode", settings.fire_mode)
	settings.shot_clock_enabled = cfg.get_value(
		"match", "shot_clock_enabled", settings.shot_clock_enabled)
