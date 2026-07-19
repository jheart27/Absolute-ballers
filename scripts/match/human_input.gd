class_name HumanInput
extends RefCounted
## Intent source for one human seat. Keyboard is device -1 (uses the kb_*
## actions from InputSetup); each gamepad is polled per-device so 2-4 local
## players never collide. Produces a PlayerIntent — the sim never reads
## Input directly.
##
## Pad layout (NBA Jam classic): A shoot/block, B pass/steal, X or RT turbo,
## Y switch. Keyboard: WASD/arrows move, K/Space shoot, J pass, L/Shift
## turbo, I switch.

const DEADZONE := 0.25
const SEAT_COLORS: Array = [
	Color(0.3, 0.85, 1.0),
	Color(1.0, 0.45, 0.4),
	Color(0.55, 1.0, 0.5),
	Color(1.0, 0.85, 0.3),
]

var device := -1
var seat := 0
var color := Color.CYAN

var _prev := {}  # joy button -> was pressed last poll


func _init(device_id: int, seat_index: int) -> void:
	device = device_id
	seat = seat_index
	color = SEAT_COLORS[seat_index % SEAT_COLORS.size()]


func poll(_delta: float) -> PlayerIntent:
	var it := PlayerIntent.new()
	if device < 0:
		it.move = Input.get_vector("kb_left", "kb_right", "kb_up", "kb_down")
		it.turbo = Input.is_action_pressed("kb_turbo")
		it.shoot_pressed = Input.is_action_just_pressed("kb_shoot")
		it.shoot_released = Input.is_action_just_released("kb_shoot")
		it.pass_pressed = Input.is_action_just_pressed("kb_pass")
		it.switch_pressed = Input.is_action_just_pressed("kb_switch")
		return it
	var mv := Vector2(
		Input.get_joy_axis(device, JOY_AXIS_LEFT_X),
		Input.get_joy_axis(device, JOY_AXIS_LEFT_Y))
	if mv.length() < DEADZONE:
		mv = Vector2.ZERO
	if Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_LEFT):
		mv.x = -1.0
	elif Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_RIGHT):
		mv.x = 1.0
	if Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_UP):
		mv.y = -1.0
	elif Input.is_joy_button_pressed(device, JOY_BUTTON_DPAD_DOWN):
		mv.y = 1.0
	it.move = mv.limit_length(1.0)
	var shoot := Input.is_joy_button_pressed(device, JOY_BUTTON_A)
	it.shoot_pressed = shoot and not _was(JOY_BUTTON_A)
	it.shoot_released = not shoot and _was(JOY_BUTTON_A)
	_prev[JOY_BUTTON_A] = shoot
	it.pass_pressed = _edge(JOY_BUTTON_B)
	it.switch_pressed = _edge(JOY_BUTTON_Y)
	it.turbo = (
		Input.is_joy_button_pressed(device, JOY_BUTTON_X)
		or Input.get_joy_axis(device, JOY_AXIS_TRIGGER_RIGHT) > 0.4
	)
	return it


func _was(btn: int) -> bool:
	return _prev.get(btn, false)


func _edge(btn: int) -> bool:
	var cur := Input.is_joy_button_pressed(device, btn)
	var was: bool = _prev.get(btn, false)
	_prev[btn] = cur
	return cur and not was
