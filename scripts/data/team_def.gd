class_name TeamDef
extends Resource
## A franchise identity: name + colors. Rosters are picked per match from the
## shared character pool (fighting-game style), so teams stay lightweight.

@export var id := ""
@export var team_name := ""
@export var short_name := ""  # 3-4 letters for the HUD
@export var primary_color := Color.WHITE
@export var secondary_color := Color.BLACK
