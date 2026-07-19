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


static func quick_default() -> MatchConfig:
	## AI-vs-AI demo config so MatchScene can run standalone (e.g. F6 in editor).
	var c := MatchConfig.new()
	c.settings = Game.settings
	var team_list: Array = Game.teams
	var chars: Array = Game.character_list()
	c.team_defs = [team_list[0], team_list[1]]
	var n: int = c.settings.team_size
	c.rosters = [chars.slice(0, n), chars.slice(n, n * 2)]
	return c
