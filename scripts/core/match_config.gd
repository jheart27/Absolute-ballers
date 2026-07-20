class_name MatchConfig
extends RefCounted
## Everything MatchScene needs to build one game. Constructed by TeamSelect
## (exhibition) or TournamentScreen, consumed once via Game.start_match().

var settings: MatchSettings
var team_defs: Array = []  # [TeamDef, TeamDef]
var rosters: Array = []  # [Array of CharacterDef, Array of CharacterDef]
var human_seats: Array = []  # [{device:int, seat:int, team:int, char_index:int}]
var ai_levels: Array = [1, 1]  # per-team AI difficulty 0..2
var context := "exhibition"  # or "tournament"


static func quick_default(match_settings: MatchSettings, team_list: Array,
		chars: Array) -> MatchConfig:
	## AI-vs-AI demo config (WATCH DEMO / running MatchScene standalone).
	## Takes its inputs as arguments: autoload access from static functions
	## is version-fragile in Godot 4, and this file is load-critical.
	var c := MatchConfig.new()
	c.settings = match_settings
	c.team_defs = [team_list[0], team_list[1]]
	var n: int = match_settings.team_size
	c.rosters = [chars.slice(0, n), chars.slice(n, n * 2)]
	return c
