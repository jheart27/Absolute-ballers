class_name DevicePoller
extends RefCounted
## Edge-detection polling for lobby/menu navigation across keyboard + pads,
## outside the focus-based UI system (Godot's built-in ui_* actions can't
## tell four gamepads apart). Device -1 is the keyboard.

var _prev := {}


func just(device: int, control: String) -> bool:
	var cur := _state(device, control)
	var key := "%d:%s" % [device, control]
	var was: bool = _prev.get(key, false)
	_prev[key] = cur
	return cur and not was


func _state(device: int, control: String) -> bool:
	if device < 0:
		match control:
			"up":
				return Input.is_action_pressed("kb_up")
			"down":
				return Input.is_action_pressed("kb_down")
			"left":
				return Input.is_action_pressed("kb_left")
			"right":
				return Input.is_action_pressed("kb_right")
			"a":
				return Input.is_action_pressed("kb_shoot")
			"b":
				return Input.is_action_pressed("kb_pass")
			"start":
				return Input.is_key_pressed(KEY_ENTER)
		return false
	match control:
		"up":
			return (
				Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_UP)
				or Input.get_joy_axis(device, JOY_AXIS_LEFT_Y) < -0.6
			)
		"down":
			return (
				Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_DOWN)
				or Input.get_joy_axis(device, JOY_AXIS_LEFT_Y) > 0.6
			)
		"left":
			return (
				Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_LEFT)
				or Input.get_joy_axis(device, JOY_AXIS_LEFT_X) < -0.6
			)
		"right":
			return (
				Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_RIGHT)
				or Input.get_joy_axis(device, JOY_AXIS_LEFT_X) > 0.6
			)
		"a":
			return Input.is_joy_button_pressed(device, JOY_BUTTON_A)
		"b":
			return Input.is_joy_button_pressed(device, JOY_BUTTON_B)
		"start":
			return Input.is_joy_button_pressed(device, JOY_BUTTON_START)
	return false
