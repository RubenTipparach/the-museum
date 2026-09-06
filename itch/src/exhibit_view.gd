## Draws the state of the four puzzles on the props scenes/exhibit.tscn places
## (tools/gen_itch_scene.py writes that scene from the layout), and animates
## them: discs turning, rings lifting and settling, pads glowing, door slabs
## sinking, a refused thing shaking. It decides nothing: every rule is in
## src/sim/puzzles.gd, and main.gd asks it and tells this what happened.
class_name ExhibitView
extends Node3D

var T: Dictionary
var L: ExhibitLayout
var x: Puzzles.Exhibit
var eyes: Array[Node3D] = []
var eye_goal: Array[float] = [0.0, 0.0, 0.0]
var rings: Array[Node3D] = []
var ring_queue: Array = [[], [], [], []]
var pads: Array[Node3D] = []
var pad_on: Array[bool] = [false, false, false, false, false, false]
var pad_glow: Array[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
var pad_pressed: Array[float] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
var slabs: Dictionary = {}       # door i -> {node, open_y}
var lamps: Dictionary = {}       # door i -> [MeshInstance3D, MeshInstance3D]
var lamp_mats: Dictionary = {}
var shakes: Array = []
var stack_cfg: Dictionary


func setup(exhibit: Puzzles.Exhibit, layout: ExhibitLayout, tuning: Dictionary) -> void:
	x = exhibit
	L = layout
	T = tuning
	stack_cfg = L.raw["props"]["stack"]
	MaterialLibrary.dress(self)
	for i in 3:
		var e: Node3D = get_node("Eyes/eye_%d" % i)
		MaterialLibrary.decal(e, "eye_disc")
		eyes.append(e)
		MaterialLibrary.decal(get_node("Stones/diagram_0/eye_%d" % i), "eye_disc")
	for sz in 4:
		rings.append(get_node("Stack/ring_%d" % sz))
	for i in 6:
		var p: Node3D = get_node("Pads/pad_%d" % i)
		MaterialLibrary.decal(p, "pad_%d" % i)
		pads.append(p)
	for n in [$Stack/glyph_0, $Stack/glyph_1, $Stones/diagram_1/word]:
		MaterialLibrary.decal(n, n.get_meta("art"))
	var lamp_table: Dictionary = DataFiles.materials()["doorLamps"]
	for kind in ["green", "red", "off"]:
		var m: StandardMaterial3D = MaterialLibrary.role("mat_door_lamp").duplicate()
		m.emission = Color(lamp_table[kind])
		m.emission_energy_multiplier = float(lamp_table["offEnergy" if kind == "off" else "onEnergy"])
		lamp_mats[kind] = m
	for d in L.doors:
		lamps[d["i"]] = [get_node("Doors/lamp_%d_0" % d["i"]), get_node("Doors/lamp_%d_1" % d["i"])]


## The door slabs live in the shell; main.gd hands them over once it has it.
func bind_slab(i: int, node: Node3D) -> void:
	slabs[i] = {"node": node, "open_y": -L.door_h - 0.1}


## Everything the state says, at once. Instant on load and on restore.
func apply(instant: bool) -> void:
	for i in 3:
		eye_goal[i] = Puzzles.pos_angle(x.gaze.pos[i])
		if instant:
			eyes[i].rotation.z = eye_goal[i]
	layout_rings(instant)
	pads_lit(x.speech.phrase(x.speech.last) if x.speech.last != "" else [])
	if instant:
		for i in 6:
			pad_glow[i] = float(T["padGlow"]) if pad_on[i] else 0.0
	refresh_stones()
	for i in slabs:
		if x.open[i]:
			slabs[i]["node"].position.y = slabs[i]["open_y"]


func ring_home(peg: int, index: int) -> Vector3:
	return Vector3(float(stack_cfg["pegX"]), float(stack_cfg["plinthTop"]) + float(stack_cfg["ringLift"]) + index * float(stack_cfg["ringStep"]),
				   float(stack_cfg["pegZ"][peg]))


func ring_hover(peg: int) -> Vector3:
	return Vector3(float(stack_cfg["pegX"]), float(T["ringHover"]), float(stack_cfg["pegZ"][peg]))


func layout_rings(instant: bool) -> void:
	for peg in 3:
		var p: Array = x.stack.pegs[peg]
		for idx in p.size():
			var size: int = p[idx]
			var h := ring_home(peg, idx)
			if instant:
				rings[size].position = h
				ring_queue[size] = []
			else:
				ring_queue[size] = [h]


func eye_turned(i: int) -> void:
	eye_goal[i] += PI / 3.0


func ring_lifted(size: int, peg: int) -> void:
	ring_queue[size] = [ring_hover(peg)]


## `via_hover`: a ring set down on another peg rises first; one put back
## where it came from goes straight home.
func ring_settled(size: int, peg: int, index: int, via_hover: bool) -> void:
	var home := ring_home(peg, index)
	ring_queue[size] = [ring_hover(peg), home] if via_hover else [home]


func pads_lit(list: Array) -> void:
	for i in 6:
		pad_on[i] = i in list
		MaterialLibrary.decal(pads[i], "pad_%d_lit" % i if pad_on[i] else "pad_%d" % i)


func pad_pressed_now(i: int) -> void:
	pad_pressed[i] = 1.0


func pads_clear() -> void:
	for i in 6:
		pad_pressed[i] = 0.0
		pad_glow[i] = 0.0


func shake(node: Node3D) -> void:
	if node:
		shakes.append({"node": node, "t": 0.0, "x": node.position.x})


func door_lamp(i: int, kind: String) -> void:
	for m in lamps[i]:
		MaterialLibrary.cover(m, lamp_mats[kind])


## The seeing stones show the three rooms behind the player as they stand.
func refresh_stones() -> void:
	for i in 3:
		var e: Node3D = get_node("Stones/diagram_0/eye_%d" % i)
		e.rotation.z = Puzzles.pos_angle(x.gaze.pos[i])
		MaterialLibrary.decal(get_node("Stones/diagram_0/numeral_%d" % i), "numeral_%d" % x.gaze.pos[i])
	var r := float(L.raw["props"]["stones"]["r"]) * 2.0
	var base := -0.22 * r
	for peg in 3:
		var p: Array = x.stack.pegs[peg]
		for idx in p.size():
			var ring: Node3D = get_node("Stones/diagram_1/ring_%d" % p[idx])
			ring.position = Vector3((0.28 + 0.22 * peg - 0.5) * r, base + 0.03 * r + idx * 0.055 * r, 0.06)
	var held: int = x.stack.held
	if held >= 0:
		get_node("Stones/diagram_1/ring_%d" % held).position = Vector3((0.28 + 0.22 * x.stack.from - 0.5) * r, base + 0.36 * r, 0.06)
	var phrase: Array = x.speech.phrase(x.speech.last) if x.speech.last != "" else []
	for k in 4:
		var w: Node3D = get_node("Stones/diagram_2/word_%d" % k)
		w.visible = k < phrase.size()
		if w.visible:
			MaterialLibrary.decal(w, "word_%d" % phrase[k])


func _process(delta: float) -> void:
	var dt := minf(delta, 0.05)
	var k := 1.0 - exp(-float(T["easeK"]) * dt)
	for i in 3:
		eyes[i].rotation.z = lerpf(eyes[i].rotation.z, eye_goal[i], k * float(T["eyeEase"]))
	for sz in 4:
		var q: Array = ring_queue[sz]
		if q.is_empty():
			continue
		var r := rings[sz]
		r.position = r.position.lerp(q[0], k * float(T["ringEase"]))
		if r.position.distance_to(q[0]) < 0.02:
			r.position = q[0]
			q.pop_front()
	for i in 6:
		var want := float(T["padGlow"]) if pad_on[i] else 0.0
		pad_glow[i] = lerpf(pad_glow[i], maxf(want, pad_pressed[i]), k)
		pad_pressed[i] = maxf(0.0, pad_pressed[i] - dt * 3.0)
		var mat := MaterialLibrary.art("pad_%d_lit" % i if pad_on[i] else "pad_%d" % i)
		mat.emission_enabled = true
		mat.emission = Color(0.9, 0.7, 0.25)
		mat.emission_energy_multiplier = pad_glow[i]
		if mat.emission_texture == null:
			mat.emission_texture = mat.albedo_texture
	for i in slabs:
		var s: Dictionary = slabs[i]
		var want_y: float = s["open_y"] if x.open[i] else 0.0
		s["node"].position.y = lerpf(s["node"].position.y, want_y, k * float(T["doorEase"]))
	for j in range(shakes.size() - 1, -1, -1):
		var s: Dictionary = shakes[j]
		s["t"] += dt
		var amp := float(T["shakeAmp"]) * maxf(0.0, float(T["shakeSeconds"]) - s["t"])
		s["node"].position.x = s["x"] + sin(s["t"] * 60.0) * amp
		if s["t"] > float(T["shakeSeconds"]):
			s["node"].position.x = s["x"]
			shakes.remove_at(j)
