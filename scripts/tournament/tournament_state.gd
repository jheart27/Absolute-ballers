class_name TournamentState
extends RefCounted
## Single-elimination 8-team bracket. The player's squad occupies one slot;
## the other seven are AI franchises with random rosters. AI-vs-AI matches
## are resolved statistically; the player's matches are played for real with
## opponent difficulty rising each round (QF rookie -> final legend).

const SIZE := 8
const ROUND_NAMES: Array = ["QUARTERFINALS", "SEMIFINALS", "GRAND FINAL"]

var entries: Array = []  # {team_def, roster, human_seats, is_player}
var rounds: Array = []  # rounds[r] = ordered entry indices alive in round r
var winners_by_round: Array = []
var current_round := 0
var player_alive := true
var champion := -1
var rng := RandomNumberGenerator.new()


func build(player_entry: Dictionary, team_defs: Array, char_pool: Array,
		team_size: int) -> void:
	rng.randomize()
	player_entry["is_player"] = true
	entries = [player_entry]
	var others: Array = team_defs.filter(
		func(td): return td != player_entry.team_def)
	others.shuffle()
	for i in SIZE - 1:
		var pool: Array = char_pool.duplicate()
		pool.shuffle()
		entries.append({
			"team_def": others[i % others.size()],
			"roster": pool.slice(0, team_size),
			"human_seats": [],
			"is_player": false,
		})
	var order: Array = [0]
	var rest: Array = range(1, SIZE)
	rest.shuffle()
	order.append_array(rest)
	rounds = [order]
	winners_by_round = []
	current_round = 0
	player_alive = true
	champion = -1


func round_name() -> String:
	return ROUND_NAMES[clampi(current_round, 0, ROUND_NAMES.size() - 1)]


func player_pair() -> Array:
	var alive: Array = rounds[current_round]
	for p in range(0, alive.size(), 2):
		if entries[alive[p]].is_player or entries[alive[p + 1]].is_player:
			return [alive[p], alive[p + 1]]
	return []


func build_player_match_config(settings: MatchSettings) -> MatchConfig:
	var pair := player_pair()
	var me: int = pair[0] if entries[pair[0]].is_player else pair[1]
	var opp: int = pair[1] if me == pair[0] else pair[0]
	var c := MatchConfig.new()
	c.settings = settings
	c.context = "tournament"
	c.team_defs = [entries[me].team_def, entries[opp].team_def]
	c.rosters = [entries[me].roster, entries[opp].roster]
	c.human_seats = entries[me].human_seats
	# player teammates follow the chosen difficulty; the bracket ramps 0->2
	c.ai_levels = [settings.difficulty, clampi(current_round, 0, 2)]
	return c


func record_player_result(player_won: bool) -> void:
	var alive: Array = rounds[current_round]
	var winners: Array = []
	for p in range(0, alive.size(), 2):
		var a: int = alive[p]
		var b: int = alive[p + 1]
		if entries[a].is_player or entries[b].is_player:
			var player_i: int = a if entries[a].is_player else b
			var other: int = b if player_i == a else a
			winners.append(player_i if player_won else other)
			if not player_won:
				player_alive = false
		else:
			winners.append(_sim_winner(a, b))
	winners_by_round.append(winners)
	rounds.append(winners)
	current_round += 1
	if winners.size() == 1:
		champion = winners[0]
		if entries[champion].is_player:
			EventBus.tournament_won.emit()
	elif not player_alive:
		_sim_out()


func _sim_out() -> void:
	## Player is eliminated: fast-forward the rest of the bracket.
	while rounds[current_round].size() > 1:
		var alive: Array = rounds[current_round]
		var winners: Array = []
		for p in range(0, alive.size(), 2):
			winners.append(_sim_winner(alive[p], alive[p + 1]))
		winners_by_round.append(winners)
		rounds.append(winners)
		current_round += 1
	champion = rounds[current_round][0]


func _sim_winner(a: int, b: int) -> int:
	var sa := _strength(a) + rng.randf_range(0.0, 40.0)
	var sb := _strength(b) + rng.randf_range(0.0, 40.0)
	return a if sa >= sb else b


func _strength(i: int) -> float:
	var total := 0.0
	for cd in entries[i].roster:
		total += cd.stat_total()
	return total * 0.3
