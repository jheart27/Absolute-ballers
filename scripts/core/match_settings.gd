class_name MatchSettings
extends Resource
## Every match-format decision lives here as data (see docs/DESIGN_DECISIONS.md).
## Defaults: 3v3, 4 quarters x 2:00, per-player fire. All of it is editable
## from the main menu or a .tres, no code changes required.

enum FireMode { PER_PLAYER, PER_TEAM }

@export_range(1, 5) var team_size := 3  # 1v1 / 2v2 / 3v3 / 5v5 all supported
@export var quarter_count := 4
@export var quarter_length_sec := 120.0
@export var fire_mode := FireMode.PER_PLAYER
@export var fire_streak_to_ignite := 3
@export var fire_baskets_before_burnout := 4
@export_range(0, 2) var difficulty := 1  # 0 rookie, 1 arcade, 2 legend
@export var shot_clock_enabled := false
@export var shot_clock_sec := 24.0
@export var auto_switch_on_pass := true
