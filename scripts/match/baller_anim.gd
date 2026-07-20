class_name BallerAnim
## THE sprite-sheet contract. tools/generate_placeholders.py and all final art
## must follow it exactly; see docs/ASSET_PIPELINE.md.
##
## Sheet: 6 columns x 9 rows of 96x96 frames, character faces RIGHT,
## feet on y=88 inside the frame. Rows in order:

const FRAME_SIZE := Vector2i(96, 96)
const SHEET_COLUMNS := 6
const FEET_Y := 88

# [animation name, frame count, fps, loops]
const ROWS: Array = [
	["idle", 4, 6.0, true],
	["run", 6, 12.0, true],
	["dribble", 6, 10.0, true],
	["jump_shot", 4, 10.0, false],
	["dunk", 6, 12.0, false],
	["block", 4, 12.0, false],
	["steal", 4, 14.0, false],
	["hurt", 4, 8.0, false],
	["celebrate", 4, 8.0, true],
]


static func build_frames(sheet_path: String) -> SpriteFrames:
	## Builds a SpriteFrames from any sheet that follows the contract.
	## This is the ONLY place frame regions are computed.
	var tex: Texture2D = Art.tex(sheet_path)
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for row_i in ROWS.size():
		var row: Array = ROWS[row_i]
		var anim: String = row[0]
		frames.add_animation(anim)
		frames.set_animation_speed(anim, row[2])
		frames.set_animation_loop(anim, row[3])
		for f in int(row[1]):
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2(
				f * FRAME_SIZE.x, row_i * FRAME_SIZE.y, FRAME_SIZE.x, FRAME_SIZE.y)
			frames.add_frame(anim, at)
	return frames


static func build_simple_strip(sheet_path: String, frame_w: int, fps: float) -> SpriteFrames:
	## For single-row FX strips (ball spin, fire aura).
	var tex: Texture2D = Art.tex(sheet_path)
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	frames.add_animation("loop")
	frames.set_animation_speed("loop", fps)
	frames.set_animation_loop("loop", true)
	var h := tex.get_height()
	for f in int(tex.get_width() / float(frame_w)):
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(f * frame_w, 0, frame_w, h)
		frames.add_frame("loop", at)
	return frames
