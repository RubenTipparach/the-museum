## One camera rig, with modes (ADR-4): `room`, orbiting a room's centre, and
## `inspect`, anchored on a thing with a little give. Two of everything: a
## goal that input writes and a value the camera is drawn from, eased toward
## it with 1 - exp(-k dt) so the ease takes the same wall time at any frame
## rate. Distance eases in log space, because zoom is multiplicative.
class_name CameraRig
extends Node3D

@onready var camera: Camera3D = $Camera3D

var T: Dictionary
var target := Vector3.ZERO
var yaw := 0.0
var pitch := 0.0
var dist := 4.0
var goal := {"target": Vector3.ZERO, "yaw": 0.0, "pitch": 0.0, "dist": 4.0}
var queue: Array = []
var mode := "room"
var room := 0
var station := ""
var anchor_yaw := 0.0
var anchor_pitch := 0.0


func setup(tuning: Dictionary) -> void:
	T = tuning
	camera.fov = float(T["fov"])
	camera.near = float(T["near"])
	camera.far = float(T["far"])


static func near_angle(a: float, ref: float) -> float:
	while a - ref > PI:
		a -= TAU
	while a - ref < -PI:
		a += TAU
	return a


func set_goal(t: Vector3, y: float, p: float, d: float) -> void:
	goal["target"] = t
	goal["yaw"] = near_angle(y, yaw)
	goal["pitch"] = p
	goal["dist"] = d


func snap() -> void:
	target = goal["target"]
	yaw = goal["yaw"]
	pitch = goal["pitch"]
	dist = goal["dist"]
	_place()


## The room's own place. Through the doorway first when there is one, so the
## camera never cuts through a wall on the way.
func go_room(r: int, view: Dictionary, door: Dictionary, instant: bool) -> void:
	mode = "room"
	station = ""
	room = r
	queue = []
	if door and not instant:
		var dp: Vector3 = door["pos"]
		dp.y = 1.5
		var dir: Vector3 = view["center"] - dp
		dir.y = 0.0
		dir = dir.normalized()
		var look := atan2(-dir.x, -dir.z)
		queue.append({"target": dp + dir * float(T["doorwayStep"]), "yaw": look, "pitch": 0.02, "dist": float(T["doorwayStep"])})
	queue.append({"target": view["center"], "yaw": view["yaw"], "pitch": view["pitch"], "dist": room_dist(view)})
	_next()
	if instant:
		snap()


func inspect(point: Vector3, normal: Vector3, d: float, station_name: String) -> void:
	var off := normal.normalized()
	mode = "inspect"
	station = station_name
	queue = []
	var y := atan2(off.x, off.z)
	var p := asin(clampf(off.y, -1.0, 1.0))
	anchor_yaw = near_angle(y, yaw)
	anchor_pitch = p
	set_goal(point, y, p, d)


## Back steps away from the object, it does not turn away from the wall: the
## yaw is kept, only the pitch comes back to the room's.
func leave(view: Dictionary) -> void:
	mode = "room"
	station = ""
	queue = []
	set_goal(view["center"], goal["yaw"], view["pitch"], room_dist(view))


func orbit(dx: float, dy: float) -> void:
	var s := float(T["orbitSens"])
	if mode == "room":
		# Standing in a room, the ROOM follows the finger: drag right and the
		# wall you are looking at slides right with your thumb, so the view
		# turns left. That is the drag half of a touch look, and it is the
		# opposite sign to inspect below, which nudges the view rather than
		# the object. Measured, not asserted: scene_test drags right and
		# reads where a plaque went, because a sign nobody can see is a sign
		# that flips silently.
		goal["yaw"] += dx * s
		goal["pitch"] = clampf(goal["pitch"] + dy * s, float(T["pitchMin"]), float(T["pitchMax"]))
	else:
		var n := float(T["inspectNudge"])
		var k := s * float(T["inspectSensScale"])
		goal["yaw"] = clampf(goal["yaw"] - dx * k, anchor_yaw - n, anchor_yaw + n)
		goal["pitch"] = clampf(goal["pitch"] + dy * k, anchor_pitch - n, anchor_pitch + n)


func zoom(factor: float) -> void:
	goal["dist"] = clampf(goal["dist"] * factor, float(T["distMin"]) * 0.6, float(T["distMax"]))


## The distance that fits a w by h extent in the current view, capped so the
## camera stays inside the room.
func fit_dist(w: float, h: float, cap: float) -> float:
	var vf := deg_to_rad(camera.fov) / 2.0
	var size := get_viewport().get_visible_rect().size
	var hf := atan(tan(vf) * size.x / size.y)
	var d := maxf(w * 0.5 / tan(hf), h * 0.5 / tan(vf)) * float(T["fitMargin"]) + float(T["fitPad"])
	return minf(cap, maxf(float(T["fitMin"]), d))


func room_dist(view: Dictionary) -> float:
	var size := get_viewport().get_visible_rect().size
	return float(view["dist"]) + (float(T["portraitExtra"]) if size.x < size.y else 0.0)


func arrived() -> bool:
	return queue.is_empty() and target.distance_to(goal["target"]) < 0.05 and absf(yaw - goal["yaw"]) < 0.01


func _next() -> void:
	var g: Dictionary = queue.pop_front()
	set_goal(g["target"], g["yaw"], g["pitch"], g["dist"])


func _process(delta: float) -> void:
	var k := 1.0 - exp(-float(T["easeK"]) * minf(delta, 0.05))
	target = target.lerp(goal["target"], k)
	yaw = lerpf(yaw, goal["yaw"], k)
	pitch = lerpf(pitch, goal["pitch"], k)
	dist = exp(lerpf(log(dist), log(goal["dist"]), k))
	if not queue.is_empty() and target.distance_to(goal["target"]) < float(T["queueArrive"]):
		_next()
	_place()


func _place() -> void:
	var off := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * dist
	camera.global_position = target + off
	camera.look_at(target, Vector3.UP)
