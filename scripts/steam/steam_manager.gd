extends Node
## Autoload "SteamManager": GodotSteam scaffold + achievement/leaderboard
## stubs. Runs happily WITHOUT the GodotSteam module — every call becomes a
## logged no-op, so the game is fully playable pre-Steam. See docs/STEAM.md
## for wiring up the real thing (and docs/ONLINE_MULTIPLAYER.md for the
## post-v1 Steamworks P2P plan).

const APP_ID := 480  # TODO: replace with the real Steam app id

# Achievement API names — keep in sync with the Steamworks partner site.
const ACH_FIRST_WIN := "ACH_FIRST_WIN"
const ACH_FIRST_DUNK := "ACH_BOOMSHAKALAKA"
const ACH_FIRST_FIRE := "ACH_SHES_ON_FIRE"
const ACH_TOURNAMENT_CHAMP := "ACH_ABSOLUTE_CHAMPION"
const LB_TOURNAMENT_WINS := "LB_TOURNAMENT_WINS"

var active := false

var _steam: Object = null
var _session_unlocks := {}  # avoid spamming the stub log / Steam API


func _ready() -> void:
	if Engine.has_singleton("Steam"):
		_steam = Engine.get_singleton("Steam")
		var init: Dictionary = _steam.call("steamInitEx", APP_ID, true)
		active = init.get("status", 1) == 0
		if not active:
			push_warning("SteamManager: steamInitEx failed: %s" % str(init))
	else:
		print("SteamManager: GodotSteam not present — running with stubs")
	EventBus.match_ended.connect(_on_match_ended)
	EventBus.fire_changed.connect(_on_fire_changed)
	EventBus.basket_scored.connect(_on_basket_scored)
	EventBus.tournament_won.connect(_on_tournament_won)


func _process(_delta: float) -> void:
	if active:
		_steam.call("run_callbacks")


# ------------------------------------------------------------------ public
func unlock_achievement(ach_id: String) -> void:
	if _session_unlocks.has(ach_id):
		return
	_session_unlocks[ach_id] = true
	if active:
		_steam.call("setAchievement", ach_id)
		_steam.call("storeStats")
	else:
		print("SteamManager (stub): unlock ", ach_id)


func upload_leaderboard(lb_id: String, score: int) -> void:
	if active:
		# TODO: findLeaderboard -> leaderboard_find_result signal ->
		# uploadLeaderboardScore. Fill in once the leaderboard exists.
		pass
	else:
		print("SteamManager (stub): leaderboard %s = %d" % [lb_id, score])


# ----------------------------------------------------------------- hookups
func _on_match_ended(_winner_team: int, winner_has_human: bool) -> void:
	if winner_has_human:
		unlock_achievement(ACH_FIRST_WIN)


func _on_fire_changed(baller, on_fire: bool) -> void:
	if on_fire and baller.is_human():
		unlock_achievement(ACH_FIRST_FIRE)


func _on_basket_scored(_team: int, _points: int, scorer, was_dunk: bool) -> void:
	if was_dunk and scorer.is_human():
		unlock_achievement(ACH_FIRST_DUNK)


func _on_tournament_won() -> void:
	unlock_achievement(ACH_TOURNAMENT_CHAMP)
	upload_leaderboard(LB_TOURNAMENT_WINS, 1)
