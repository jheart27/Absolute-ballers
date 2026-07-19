class_name CharacterDef
extends Resource
## Data-driven baller definition. The sprite sheet path lives HERE and only
## here — gameplay code never hardcodes art paths. Swapping placeholder art
## for final pixel art = editing sprite_sheet (or replacing the PNG in place),
## provided the sheet follows the contract in scripts/match/baller_anim.gd.

@export var id := ""
@export var display_name := ""
@export var tagline := ""
@export_file("*.png") var sprite_sheet := ""
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
