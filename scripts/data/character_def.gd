class_name CharacterDef
extends Resource
## Data-driven baller definition. The sprite sheet paths live HERE and only
## here — gameplay code never hardcodes art paths. Sheets are baked by the
## chibi rig (python3 -m tools.chibi_rig bake) and follow the generated
## BallerSheet contract; see docs/ASSET_PIPELINE.md.

@export var id := ""
@export var display_name := ""
@export var tagline := ""
## The girl, with her team kit painted black.
@export_file("*.png") var sprite_sheet := ""
## The kit alone in gray (same layout), tinted with the team color in-game.
## Leave empty for a sheet whose uniform is already painted in.
@export_file("*.png") var kit_sheet := ""
@export var ui_color := Color.WHITE

@export_group("Stats (0-10)")
@export_range(0, 10) var speed := 5
@export_range(0, 10) var three_point := 5
@export_range(0, 10) var dunk := 5
@export_range(0, 10) var power := 5
@export_range(0, 10) var steal := 5
@export_range(0, 10) var block := 5


func stat_total() -> int:
	return speed + three_point + dunk + power + steal + block
