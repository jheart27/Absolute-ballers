extends Node
## Root of the main scene. Autoloads are ready by the time this runs;
## it simply hands off to the menu flow and stays as an inert anchor node.


func _ready() -> void:
	Game.goto_main_menu.call_deferred()
