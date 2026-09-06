## A fixed pool of lights that follows the room the player is in, so the
## shader never compiles for a new light count and a phone never pays for
## lights it cannot see (ADR-3): one room lamp, a track head on every plaque
## and station in the room, a coloured wash on each door lamp, and a head over
## the door that leads on. The nodes are authored in main.tscn; this aims them.
class_name LightPool
extends Node3D

@onready var lamp: OmniLight3D = $Lamp
@onready var spots: Array[SpotLight3D] = [$Spot0, $Spot1, $Spot2, $Spot3, $Spot4]
@onready var door_lights: Array[OmniLight3D] = [$Door0, $Door1]
@onready var way: SpotLight3D = $Way

var L: ExhibitLayout
var T: Dictionary


func setup(layout: ExhibitLayout, tuning: Dictionary) -> void:
	L = layout
	T = tuning["lights"]
	lamp.light_energy = float(T["lamp"]["energy"])
	lamp.omni_range = float(T["lamp"]["range"])
	for s in spots:
		s.spot_range = float(T["spot"]["range"])
		s.spot_angle_attenuation = float(T["spot"]["penumbra"])
	for d in door_lights:
		d.omni_range = float(T["doorLamp"]["range"])
	way.spot_range = float(T["way"]["range"])
	way.spot_angle = float(T["way"]["angle"])
	way.spot_angle_attenuation = float(T["spot"]["penumbra"])


## The room lamp and the track heads: every plaque in the room, then its
## station, then anything the layout lists as an extra aim.
func place(room: int) -> void:
	var view: Dictionary = L.views[room]
	lamp.global_position = view["lamp"]
	var so := float(L.raw["fixtures"]["lighting"]["standoff"])
	var y := float(L.raw["fixtures"]["truss"]["y"]) - 0.4
	var aims: Array = []
	for p in L.raw["plaques"]:
		if L.room_of(DataFiles.v3(p["pos"])) == room:
			aims.append([DataFiles.v3(p["pos"]), DataFiles.v3(p["normal"]), T["plaqueSpot"][0], T["plaqueSpot"][1]])
	for k in L.stations:
		var st: Dictionary = L.stations[k]
		if st["room"] == room:
			aims.append([st["point"], st["normal"], T["stationSpot"][0], T["stationSpot"][1]])
	for a in L.raw["views"]["extraSpots"].get(str(room), []):
		aims.append([DataFiles.v3(a[0]), DataFiles.v3(a[1]), a[2], a[3]])
	for i in spots.size():
		var s := spots[i]
		if i >= aims.size():
			s.visible = false
			continue
		var point: Vector3 = aims[i][0]
		var n: Vector3 = aims[i][1]
		var flat := Vector2(n.x, n.z)
		if flat.length() < 0.001:
			flat = Vector2(0, 1)
		flat = flat.normalized()
		s.visible = true
		s.global_position = Vector3(point.x + flat.x * so, y, point.z + flat.y * so)
		s.look_at(point, Vector3.UP)
		s.light_energy = float(aims[i][2]) * float(T["spot"]["scale"])
		s.spot_angle = rad_to_deg(float(aims[i][3]))


## The door washes and the way on. `lit` is [[door, colour], ...] for the
## doors that show a colour from this room, `way_door` the open door that
## leads deeper, or empty.
func doors(room: int, lit: Array, way_door: Dictionary) -> void:
	var view: Dictionary = L.views[room]
	for k in door_lights.size():
		var dl := door_lights[k]
		if k >= lit.size():
			dl.visible = false
			continue
		var d: Dictionary = lit[k][0]
		var out := L.door_side(d, view["center"])
		dl.visible = true
		dl.global_position = d["pos"] + out * 0.45 + Vector3(0, L.door_h + 0.05, 0)
		dl.light_color = lit[k][1]
		dl.light_energy = float(T["doorLamp"]["energy"])
	if way_door.is_empty():
		way.visible = false
		return
	var out := L.door_side(way_door, view["center"])
	way.visible = true
	way.global_position = way_door["pos"] + out * 1.15 + Vector3(0, float(L.raw["fixtures"]["truss"]["y"]) - 0.4, 0)
	way.look_at(way_door["pos"] + out * 0.12 + Vector3(0, 1.35, 0), Vector3.UP)
	way.light_energy = float(T["way"]["energy"])
