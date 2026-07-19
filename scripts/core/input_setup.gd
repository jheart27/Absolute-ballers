class_name InputSetup
## Registers keyboard actions in code so project.godot stays minimal and the
## mapping is greppable. Gamepads are NOT routed through actions: every pad is
## polled per-device in HumanInput so 2-4 local players never collide.
## The keyboard is "device -1" and uses these actions.
##
## Layout (NBA Jam classic, context-sensitive):
##   SHOOT  = offense: jump + shot meter / dunk   defense: block jump
##   PASS   = offense: pass                        defense: steal lunge
##   TURBO  = hold to sprint (drains turbo meter; unlimited while on fire)
##   SWITCH = take over the teammate nearest the ball

const KEY_ACTIONS := {
	"kb_up": [KEY_W, KEY_UP],
	"kb_down": [KEY_S, KEY_DOWN],
	"kb_left": [KEY_A, KEY_LEFT],
	"kb_right": [KEY_D, KEY_RIGHT],
	"kb_shoot": [KEY_K, KEY_SPACE],
	"kb_pass": [KEY_J],
	"kb_turbo": [KEY_L, KEY_SHIFT],
	"kb_switch": [KEY_I],
	"ui_pause": [KEY_ESCAPE, KEY_P],
}


static func install() -> void:
	for action in KEY_ACTIONS:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in KEY_ACTIONS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
