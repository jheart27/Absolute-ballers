# Steam integration (scaffold)

`SteamManager` (autoload, `scripts/steam/steam_manager.gd`) is a
GodotSteam scaffold that runs with or without the module: absent Steam,
every call is a logged no-op, so the game is fully playable pre-Steam.

## Wiring up the real thing

1. Install GodotSteam — either the precompiled editor build from
   https://godotsteam.com or the GDExtension addon into `addons/`.
2. Set `APP_ID` in steam_manager.gd (currently 480 = Spacewar test app).
3. Drop `steam_appid.txt` (the app id) next to the editor binary for dev.
4. Create the achievements below on the Steamworks partner site with
   matching API names, then test — `unlock_achievement` already calls
   `setAchievement`/`storeStats` when Steam is live.

## Achievement stubs (wired to EventBus already)

| API name | Trigger (already implemented) |
|---|---|
| `ACH_FIRST_WIN` | a human-controlled team wins a match |
| `ACH_BOOMSHAKALAKA` | first human dunk |
| `ACH_SHES_ON_FIRE` | a human baller catches fire |
| `ACH_ABSOLUTE_CHAMPION` | win the tournament |

Add more by connecting EventBus signals in `SteamManager._ready`.

## Leaderboard stubs

`upload_leaderboard(LB_TOURNAMENT_WINS, n)` is called on tournament wins;
the GodotSteam find/upload signal round-trip is a TODO in the function
body (needs the leaderboard to exist on the partner site first).

Online multiplayer via Steamworks P2P is a **post-v1 milestone** — see
`docs/ONLINE_MULTIPLAYER.md`.
