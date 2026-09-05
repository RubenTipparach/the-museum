## The one place the data files are spelled (CLAUDE.md 4.1). Everything the
## exhibit reads from data/ comes through here, parsed once and cached.
class_name DataFiles
extends RefCounted

const LAYOUT := "res://data/layout/elmorian.json"
const LORE := "res://data/lore/elmorian.json"
const TUNING := "res://data/tuning.json"
const MATERIALS := "res://data/materials.json"

static var _cache: Dictionary = {}


static func read(path: String) -> Dictionary:
	if _cache.has(path):
		return _cache[path]
	var text := FileAccess.get_file_as_string(path)
	assert(text != "", "missing data file " + path)
	var parsed = JSON.parse_string(text)
	assert(parsed is Dictionary, "not a JSON object: " + path)
	_cache[path] = parsed
	return parsed


static func layout() -> Dictionary:
	return read(LAYOUT)


static func lore() -> Dictionary:
	return read(LORE)


static func tuning() -> Dictionary:
	return read(TUNING)


static func materials() -> Dictionary:
	return read(MATERIALS)


static func v3(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])
