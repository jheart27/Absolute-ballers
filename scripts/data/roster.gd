class_name Roster
## Loads every .tres in the data folders. Adding a character or team to the
## game = dropping a .tres file in — nothing to register in code.

const CHAR_DIR := "res://data/characters"
const TEAM_DIR := "res://data/teams"


static func load_characters() -> Dictionary:
	var out := {}
	for res in _load_dir(CHAR_DIR):
		if res is CharacterDef:
			out[res.id] = res
	return out


static func load_teams() -> Array:
	var out := []
	for res in _load_dir(TEAM_DIR):
		if res is TeamDef:
			out.append(res)
	return out


static func _load_dir(path: String) -> Array:
	var out := []
	var dir := DirAccess.open(path)
	if dir == null:
		push_error("Roster: cannot open %s" % path)
		return out
	var names: Array = []
	for f in dir.get_files():
		var fname := f.trim_suffix(".remap")  # exported builds list remapped names
		if fname.ends_with(".tres"):
			names.append(fname)
	names.sort()  # deterministic load order
	for fname in names:
		var res: Resource = ResourceLoader.load(path.path_join(fname))
		if res != null:
			out.append(res)
	return out
