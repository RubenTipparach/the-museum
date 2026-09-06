## The one writer of the save (CLAUDE.md 4.1): the exhibit's state and the
## room the player is in, as JSON in user://, which the web export keeps in
## the browser's storage. Nothing derived is written (ADR-2).
class_name SaveFile
extends RefCounted

const PATH := "user://elmorian-exhibit-v1.json"


static func write(state: Dictionary) -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(state))
		f.close()


static func read() -> Dictionary:
	if not FileAccess.file_exists(PATH):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	return parsed if parsed is Dictionary else {}


static func clear() -> void:
	if FileAccess.file_exists(PATH):
		DirAccess.remove_absolute(PATH)
