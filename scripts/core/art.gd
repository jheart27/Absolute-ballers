class_name Art
## Texture loading with a loud, visible fallback. If an asset is missing or
## the editor hasn't finished importing yet, gameplay keeps running with a
## magenta placeholder instead of crashing on a null texture — and the exact
## path lands in the error log.

static var _fallback: Texture2D = null


static func tex(path: String) -> Texture2D:
	var t: Texture2D = null
	if ResourceLoader.exists(path):
		t = load(path)
	if t != null:
		return t
	push_error(
		"Art: missing texture '%s' — using magenta fallback " % path
		+ "(did the editor finish importing assets?)")
	if _fallback == null:
		var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
		img.fill(Color(1.0, 0.0, 0.8, 1.0))
		_fallback = ImageTexture.create_from_image(img)
	return _fallback
