## Typed questions about data/layout/elmorian.json: which room a point is in,
## where a door is, where the camera stands in a room. The one reader of the
## layout, so its shape is known in one place.
class_name ExhibitLayout
extends RefCounted

var raw: Dictionary
var door_w: float
var door_h: float
var doors: Array = []          # {i, pos: Vector3, axis, rooms: [a, b], slab}
var views: Array = []          # by room: {center: Vector3, yaw, pitch, dist, lamp: Vector3}
var stations: Dictionary = {}  # by name: {point, normal, w, h, cap, room}


func _init(layout: Dictionary) -> void:
	raw = layout
	door_w = layout["door"]["w"]
	door_h = layout["door"]["h"]
	for d in layout["doors"]:
		doors.append({"i": int(d["i"]), "pos": Vector3(d["at"][0], 0.0, d["at"][1]), "axis": d["axis"],
					  "rooms": [int(d["rooms"][0]), int(d["rooms"][1])], "slab": d["slab"]})
	for v in layout["views"]["rooms"]:
		views.append({"center": DataFiles.v3(v["center"]), "yaw": float(v["yaw"]), "pitch": float(v["pitch"]),
					  "dist": float(v["dist"]), "lamp": DataFiles.v3(v["lamp"])})
	for k in layout["stations"]:
		if k == "_":
			continue
		var s: Dictionary = layout["stations"][k]
		stations[k] = {"point": DataFiles.v3(s["point"]), "normal": DataFiles.v3(s["normal"]), "w": float(s["w"]),
					   "h": float(s["h"]), "cap": float(s["cap"]), "room": int(s["room"])}


func room_of(p: Vector3) -> int:
	for r in raw["rooms"]:
		var b: Array = r["bounds"]
		if p.x >= b[0] and p.x <= b[2] and p.z >= b[1] and p.z <= b[3]:
			return int(r["id"])
	return -1


func plaque(id: String) -> Dictionary:
	for p in raw["plaques"]:
		if p["id"] == id:
			return p
	return {}


func plaque_normal(id: String) -> Vector3:
	var p := plaque(id)
	return Vector3(p["normal"][0], 0.0, p["normal"][2]) if p else Vector3.ZERO


## The door between two rooms, or an empty dictionary.
func door_between(a: int, b: int) -> Dictionary:
	for d in doors:
		if (d["rooms"][0] == a and d["rooms"][1] == b) or (d["rooms"][1] == a and d["rooms"][0] == b):
			return d
	return {}


## The side of a door that faces a point: the door's outward axis, signed.
func door_side(d: Dictionary, toward: Vector3) -> Vector3:
	var out := Vector3(0, 0, 1) if d["axis"] == "x" else Vector3(1, 0, 0)
	var to: Vector3 = toward - d["pos"]
	to.y = 0.0
	return out * (1.0 if to.dot(out) >= 0.0 else -1.0)
