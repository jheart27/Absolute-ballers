extends Node
## Autoload "AudioManager": tiny SFX engine over the generated placeholder
## WAVs in assets/placeholder/audio (filenames are the contract — final
## sound design replaces the files 1:1). Presentation-side: it listens to
## EventBus for most cues; the few direct calls from the sim (ball bounces,
## whooshes) are fire-and-forget and never affect game state.
## Missing audio degrades to silence, never to a crash.

const AUDIO_DIR := "res://assets/placeholder/audio"
const VOICES := 12

var _streams := {}  # basename -> AudioStream
var _players: Array = []
var _next := 0
var _ambient: AudioStreamPlayer


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in VOICES:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)
	_ambient = AudioStreamPlayer.new()
	_ambient.volume_db = -18.0
	add_child(_ambient)
	_load_streams()
	EventBus.basket_scored.connect(_on_basket_scored)
	EventBus.shot_blocked.connect(_on_shot_blocked)
	EventBus.steal_made.connect(_on_steal_made)
	EventBus.knockdown.connect(_on_knockdown)
	EventBus.fire_changed.connect(_on_fire_changed)
	EventBus.match_ended.connect(_on_match_ended)


func _load_streams() -> void:
	var dir := DirAccess.open(AUDIO_DIR)
	if dir == null:
		push_warning("AudioManager: %s missing — sounds disabled" % AUDIO_DIR)
		return
	for f in dir.get_files():
		var fname := f.trim_suffix(".remap")
		if not fname.ends_with(".wav"):
			continue
		var stream: AudioStream = load(AUDIO_DIR.path_join(fname))
		if stream == null:
			continue
		var sfx_name := fname.trim_suffix(".wav")
		if sfx_name == "crowd_loop" and stream is AudioStreamWAV:
			stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
			stream.loop_begin = 0
			stream.loop_end = stream.data.size() / 2  # 16-bit mono frames
		_streams[sfx_name] = stream


func play(sfx_name: String, volume_db := 0.0, pitch_jitter := 0.06) -> void:
	var stream = _streams.get(sfx_name)
	if stream == null:
		return
	var p: AudioStreamPlayer = _players[_next]
	_next = (_next + 1) % VOICES
	p.stream = stream
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	p.play()


func start_ambient() -> void:
	var stream = _streams.get("crowd_loop")
	if stream == null or _ambient.playing:
		return
	_ambient.stream = stream
	_ambient.play()


func stop_ambient() -> void:
	_ambient.stop()


# ------------------------------------------------------------------- hooks
func _on_basket_scored(_team: int, points: int, _scorer, was_dunk: bool) -> void:
	if was_dunk:
		play("slam", 0.0)
		play("cheer", -4.0)
	elif points == 3:
		play("swish", -2.0)
		play("cheer", -7.0)
	else:
		play("swish", -4.0)


func _on_shot_blocked(_blocker, _shooter) -> void:
	play("block", -2.0)


func _on_steal_made(_stealer, _victim) -> void:
	play("steal", -5.0)


func _on_knockdown(_victim) -> void:
	play("knockdown", -2.0)


func _on_fire_changed(_baller, on_fire: bool) -> void:
	if on_fire:
		play("fire_ignite", -2.0)


func _on_match_ended(_winner: int, _has_human: bool) -> void:
	play("buzzer", -2.0)
	play("cheer", -3.0)
	stop_ambient()
