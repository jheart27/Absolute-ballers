class_name HumanInput
extends RefCounted
## Intent source for one human seat. Keyboard is device -1 (uses the kb_*
## actions from InputSetup); each gamepad is polled per-device so 2-4 local
## players never collide. Device -2 is the SOLO seat: keyboard AND the first
## gamepad both drive it, so single-player Just Works however you're holding
## the machine. Produces a PlayerIntent — the sim never reads Input directly.
##
## Pad layout (NBA Jam classic): A shoot/block, B pass/steal, X or RT turbo,
## Y switch. Keyboard: WASD/arrows move, K/Space shoot, J pass, L/Shift
## turbo, I switch.

const SOLO_DEVICE := -2

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


func _pad_id() -> int:
	## Physical pad this seat polls, or -1 if none. SOLO_DEVICE borrows pad 0.
	if device == SOLO_DEVICE:
		var pads := Input.get_connected_joypads()
		return pads[0] if not pads.is_empty() else -1
	return device


func _uses_keyboard() -> bool:
	return device == -1 or device == SOLO_DEVICE


func poll(_delta: float) -> PlayerIntent:
	var it := PlayerIntent.new()
	if _uses_keyboard():
		it.move = Input.get_vector("kb_left", "kb_right", "kb_up", "kb_down")
		it.turbo = Input.is_action_pressed("kb_turbo")
		it.shoot_pressed = Input.is_action_just_pressed("kb_shoot")
		it.shoot_released = Input.is_action_just_released("kb_shoot")
		it.pass_pressed = Input.is_action_just_pressed("kb_pass")
		it.switch_pressed = Input.is_action_just_pressed("kb_switch")
	var pad := _pad_id()
	if pad >= 0:
		_poll_pad(pad, it)  # ORs the pad in on top of any keyboard input
	return it


func _poll_pad(pad: int, it: PlayerIntent) -> void:
	var mv := Vector2(
		Input.get_joy_axis(pad, JOY_AXIS_LEFT_X),
		Input.get_joy_axis(pad, JOY_AXIS_LEFT_Y))
	if mv.length() < DEADZONE:
		mv = Vector2.ZERO
	if Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_LEFT):
		mv.x = -1.0
	elif Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_RIGHT):
		mv.x = 1.0
	if Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_UP):
		mv.y = -1.0
	elif Input.is_joy_button_pressed(pad, JOY_BUTTON_DPAD_DOWN):
		mv.y = 1.0
	if mv.length() > it.move.length():
		it.move = mv.limit_length(1.0)
	var shoot := Input.is_joy_button_pressed(pad, JOY_BUTTON_A)
	it.shoot_pressed = it.shoot_pressed or (shoot and not _was(JOY_BUTTON_A))
	it.shoot_released = it.shoot_released or (not shoot and _was(JOY_BUTTON_A))
	_prev[JOY_BUTTON_A] = shoot
	it.pass_pressed = it.pass_pressed or _edge(pad, JOY_BUTTON_B)
	it.switch_pressed = it.switch_pressed or _edge(pad, JOY_BUTTON_Y)
	it.turbo = it.turbo or (
		Input.is_joy_button_pressed(pad, JOY_BUTTON_X)
		or Input.get_joy_axis(pad, JOY_AXIS_TRIGGER_RIGHT) > 0.4
	)


func _was(btn: int) -> bool:
	return _prev.get(btn, false)


func _edge(pad: int, btn: int) -> bool:
	var cur := Input.is_joy_button_pressed(pad, btn)
	var was: bool = _prev.get(btn, false)
	_prev[btn] = cur
	return cur and not was
