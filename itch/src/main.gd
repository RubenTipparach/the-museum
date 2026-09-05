## The exhibit, wired: the puzzles (src/sim/puzzles.gd), the camera rig, the
## light pool, the view of the props, the HUD, the audio, the save. This file
## routes a tap to the thing it landed on and tells the others what happened.
## It holds no rule of its own: what a tap does to a puzzle is the sim's
## answer, and what that answer looks like is the view's (ADR-2, CLAUDE.md 9).
extends Node3D

@onready var rig: CameraRig = $Rig
@onready var lights: LightPool = $Lights
@onready var view: ExhibitView = $Exhibit
@onready var shell: Node3D = $Shell
@onready var hud: Hud = $HUD
@onready var audio: AudioBank = $Audio

var T: Dictionary
var L: ExhibitLayout
var lore: Dictionary
var x := Puzzles.Exhibit.new()
var was_open: Array = []
var last_card: Dictionary = {}
var reset_armed := false
var bodies: Array[Node3D] = []
var bridge: DebugBridge

var pointers: Dictionary = {}
var drag: Dictionary = {}
var pinch_d := 0.0


func _ready() -> void:
	T = DataFiles.tuning()
	L = ExhibitLayout.new(DataFiles.layout())
	lore = DataFiles.lore()
	rig.setup(T)
	lights.setup(L, T)
	view.setup(x, L, T)
	_dress_shell()
	_collect_bodies(self)
	hud.close_pressed.connect(hide_card)
	hud.read_pressed.connect(func() -> void:
		if not last_card.is_empty():
			show_card(last_card["title"], last_card["text"]))
	hud.back_pressed.connect(leave_inspect)
	hud.restart_pressed.connect(_restart)
	hud.about_pressed.connect(func() -> void: show_card(lore["arch"]["title"], lore["arch"]["text"]))
	hud.chip_pressed.connect(func(i: int) -> void:
		if can_reach(i):
			go_room(i, false)
			audio.play("step")
		else:
			audio.play("thud"))
	get_viewport().size_changed.connect(_on_resize)
	_on_resize()
	was_open = x.open.duplicate()
	view.apply(true)
	if not _load():
		go_room(0, true)
	bridge = DebugBridge.new(self)
	print("MUSEUM_SMOKE_OK")


## The shell's parts are named for what they are; bind their pictures and
## hand the door slabs to the view.
func _dress_shell() -> void:
	MaterialLibrary.dress(shell)
	var door := RegEx.create_from_string("^door_(\\d+)_slab$")
	for mi in MaterialLibrary.meshes(shell):
		if mi.name.begins_with("plaque_"):
			MaterialLibrary.cover(mi, MaterialLibrary.art("plaque_" + mi.name.substr(7)))
		elif mi.name == "sign_hall":
			MaterialLibrary.cover(mi, MaterialLibrary.art("sign_hall"))
		var m := door.search(mi.name)
		if m:
			view.bind_slab(int(m.get_string(1)), mi)


func _collect_bodies(node: Node) -> void:
	if node is StaticBody3D and node.has_meta("kind"):
		bodies.append(node)
	for c in node.get_children():
		_collect_bodies(c)


# ---- rooms and stations ----------------------------------------------------------------
func go_room(r: int, instant: bool) -> void:
	var from := rig.room
	last_card = {}
	hud.hide_card()
	hud.set_tools(false, false)
	hud.set_inspecting(false)
	rig.go_room(r, L.views[r], L.door_between(from, r), instant)
	lights.place(r)
	refresh_door_lamps()
	update_hud()
	save()
	if r == 5:
		get_tree().create_timer(float(T["endCardMs"]) / 1000.0).timeout.connect(func() -> void:
			if rig.room == 5:
				show_card(lore["end"]["title"], lore["end"]["text"]))


func inspect(point: Vector3, normal: Vector3, d: float, station: String) -> void:
	rig.inspect(point, normal, d, station)
	hud.set_tools(false if hud.card_visible() else not last_card.is_empty(), true)
	hud.set_inspecting(true)


func leave_inspect() -> void:
	rig.leave(L.views[rig.room])
	last_card = {}
	hud.hide_card()
	hud.set_tools(false, false)
	hud.set_inspecting(false)


func go_station(name: String) -> void:
	var s: Dictionary = L.stations[name]
	inspect(s["point"], s["normal"], rig.fit_dist(s["w"], s["h"], s["cap"]), name)


# ---- the card -----------------------------------------------------------------------------
## Closing the label is not leaving the object: the camera stays where it is
## so the thing can be looked at, and Read brings the label back.
func show_card(title: String, text: String) -> void:
	last_card = {"title": title, "text": text}
	hud.show_card(title, text)


func hide_card() -> void:
	hud.hide_card()
	hud.set_tools(not last_card.is_empty() and rig.mode == "inspect", rig.mode == "inspect")


# ---- input -------------------------------------------------------------------------------------
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		_touch(event as InputEventScreenTouch)
	elif event is InputEventScreenDrag:
		_drag(event as InputEventScreenDrag)
	elif event is InputEventMouseButton and event.is_pressed():
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			rig.zoom(float(T["wheelStep"]))
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			rig.zoom(1.0 / float(T["wheelStep"]))


func _touch(e: InputEventScreenTouch) -> void:
	if e.pressed:
		pointers[e.index] = e.position
		if pointers.size() == 1:
			drag = {"x": e.position.x, "y": e.position.y, "sx": e.position.x, "sy": e.position.y,
					"t": Time.get_ticks_msec(), "moved": false}
		elif pointers.size() == 2:
			var ps := pointers.values()
			pinch_d = (ps[0] as Vector2).distance_to(ps[1])
			drag = {}
		audio.wake()
		return
	var was := pointers.has(e.index)
	pointers.erase(e.index)
	if not drag.is_empty() and was and not drag["moved"] and Time.get_ticks_msec() - int(drag["t"]) < int(T["tapMs"]):
		tap(e.position)
	if pointers.is_empty():
		drag = {}
		pinch_d = 0.0


func _drag(e: InputEventScreenDrag) -> void:
	if not pointers.has(e.index):
		return
	pointers[e.index] = e.position
	if pointers.size() >= 2:
		var ps := pointers.values()
		var d: float = (ps[0] as Vector2).distance_to(ps[1])
		if pinch_d > 0.0:
			rig.zoom(pinch_d / d)
		pinch_d = d
		return
	if drag.is_empty():
		return
	var dx: float = e.position.x - float(drag["x"])
	var dy: float = e.position.y - float(drag["y"])
	drag["x"] = e.position.x
	drag["y"] = e.position.y
	if Vector2(e.position.x - float(drag["sx"]), e.position.y - float(drag["sy"])).length() > float(T["tapPx"]):
		drag["moved"] = true
	if drag["moved"]:
		rig.orbit(dx, dy)


func tap(pos: Vector2) -> void:
	hud.hint_gone()
	var h := Interaction.resolve(rig.camera, pos, T)
	if h.is_empty() or h["kind"] == "solid":
		if rig.mode == "inspect":
			leave_inspect()
		return
	match h["kind"]:
		"door", "doorway":
			var i: int = h["i"]
			var d: Dictionary = L.doors[i]
			if not x.open[i]:
				show_card(lore["doors"][i]["title"], lore["doors"][i]["text"])
				view.shake(view.slabs[i]["node"] if view.slabs.has(i) else null)
				audio.play("thud")
				return
			go_room(d["rooms"][1] if d["rooms"][0] == rig.room else d["rooms"][0], false)
			audio.play("step")
		"plaque":
			var id: String = h["id"]
			show_card(lore["plaques"][id]["title"], lore["plaques"][id]["text"])
			inspect(h["centre"], L.plaque_normal(id), rig.fit_dist(1.5, 1.1, 4.0), "plaque")
			audio.play("ui_click")
		"stone":
			show_card("Seeing stone", "It shows a room behind you as that room stands now.")
			go_station("final")
			audio.play("ui_click")
		"eye":
			if rig.station != "gaze":
				go_station("gaze")
				audio.play("ui_click")
				return
			x.gaze.tap(h["i"])
			view.eye_turned(h["i"])
			audio.play("eye_tick_%d" % h["i"])
			after_change()
		"stack":
			if rig.station != "stack":
				go_station("stack")
				audio.play("ui_click")
				return
			if h["peg"] >= 0:
				stack_tap(h["peg"])
		"pad":
			if rig.station != "speech":
				go_station("speech")
				audio.play("ui_click")
				return
			pad_tap(h["i"])


func stack_tap(peg: int) -> void:
	var held_before := x.stack.held
	var r := x.stack.tap(peg)
	match r:
		"empty":
			audio.play("thud")
		"lift":
			view.ring_lifted(x.stack.held, peg)
			audio.play("lift")
		"refuse":
			view.shake(view.rings[held_before])
			audio.play("thud")
		_:
			var p: Array = x.stack.pegs[peg]
			view.ring_settled(p[p.size() - 1], peg, p.size() - 1, r == "drop")
			audio.play("drop")
			after_change()


func pad_tap(i: int) -> void:
	var r := x.speech.tap(i)
	view.pad_pressed_now(i)
	audio.play("pad_%d" % i)
	match r:
		"wrong":
			view.pads_lit([])
			get_tree().create_timer(float(T["wrongPadMs"]) / 1000.0).timeout.connect(func() -> void:
				view.pads_clear()
				audio.play("thud"))
		"ok":
			view.pads_lit(x.speech.input)
		_:
			view.pads_lit(x.speech.phrase(r))
			audio.play("chime")
			after_change()


func after_change() -> void:
	x.refresh_doors()
	view.refresh_stones()
	refresh_door_lamps()
	save()
	for i in 5:
		if x.open[i] and not was_open[i]:
			audio.play("door_chime")
			audio.play("door_open")
			hud.toast("The ancestor door opens" if i == 4 else "A door opens", float(T["toastMs"]) / 1000.0)
	was_open = x.open.duplicate()
	update_hud()


## Green means this door has opened and leads deeper; red means it goes back
## the way you came; dark means it is still shut. rooms[0] is always the
## nearer room, so from rooms[0] a door leads on.
func refresh_door_lamps() -> void:
	var table: Dictionary = DataFiles.materials()["doorLamps"]
	var lit: Array = []
	var way: Dictionary = {}
	for d in L.doors:
		var i: int = d["i"]
		var kind := "off"
		if rig.room in d["rooms"]:
			kind = "red" if d["rooms"][1] == rig.room else ("green" if x.open[i] else "off")
		view.door_lamp(i, kind)
		if kind != "off" and lit.size() < 2:
			lit.append([d, Color(table[kind])])
		if d["rooms"][0] == rig.room and x.open[i]:
			way = d
	lights.doors(rig.room, lit, way)


# ---- HUD state -----------------------------------------------------------------------------------
## Fast travel offers every room already reached, the newest one included:
## reaching room i needs the doors behind it open, not the door out of it.
func can_reach(i: int) -> bool:
	for k in range(1, mini(i, 5)):
		if not x.open[k]:
			return false
	return true


func update_hud() -> void:
	var names: Array = []
	for r in lore["rooms"]:
		names.append(r["name"])
	hud.set_room(lore["rooms"][rig.room]["sub"], lore["rooms"][rig.room]["name"], names)
	var reach: Array = []
	for i in 6:
		reach.append(can_reach(i))
	hud.set_chips(rig.room, reach)


func _restart() -> void:
	if not reset_armed:
		reset_armed = true
		hud.restart_armed(true)
		get_tree().create_timer(float(T["resetArmMs"]) / 1000.0).timeout.connect(func() -> void:
			reset_armed = false
			hud.restart_armed(false))
		return
	SaveFile.clear()
	get_tree().reload_current_scene()


## The HUD is laid out for a 390 unit short side; on a big screen the scale
## is capped. A resize also re-fits whatever the camera is framing.
func _on_resize() -> void:
	var size := get_viewport().get_visible_rect().size
	var hud_t: Dictionary = T["hud"]
	var auto_scale := minf(size.x, size.y) / float(hud_t["baseSide"])
	get_tree().root.content_scale_factor = minf(1.0, float(hud_t["maxScale"]) / maxf(auto_scale, 0.001))
	if rig.mode == "inspect" and L.stations.has(rig.station):
		var st: Dictionary = L.stations[rig.station]
		rig.goal["dist"] = rig.fit_dist(st["w"], st["h"], st["cap"])
	elif rig.mode == "room" and rig.queue.is_empty():
		rig.goal["dist"] = rig.room_dist(L.views[rig.room])


# ---- the save: the state, not the scene -----------------------------------------------------
func save() -> void:
	var d := x.to_dict()
	d["room"] = rig.room
	SaveFile.write(d)


func _load() -> bool:
	var s := SaveFile.read()
	if s.is_empty():
		return false
	x.from_dict(s)
	view.apply(true)
	was_open = x.open.duplicate()
	go_room(mini(int(s.get("room", 0)), 4), true)
	hud.hint_gone()
	return true


# ---- observed by the playthrough, never driven -----------------------------------------------
func debug_state() -> Dictionary:
	return {"room": rig.room, "mode": rig.mode, "station": rig.station, "arrived": rig.arrived(),
			"open": x.open, "gaze": x.gaze.pos, "pegs": x.stack.pegs, "held": x.stack.held, "last": x.speech.last,
			"card": hud.card_visible(), "size": [get_viewport().get_visible_rect().size.x, get_viewport().get_visible_rect().size.y]}


func screen_of(kind: String, i, id: String) -> Variant:
	for b in bodies:
		if String(b.get_meta("kind")) != kind:
			continue
		if i != null and int(b.get_meta("i", b.get_meta("peg", -1))) != int(i):
			continue
		if id != "" and String(b.get_meta("id", "")) != id:
			continue
		var c := Interaction.centre_of(b)
		var p := rig.camera.unproject_position(c)
		return {"x": p.x, "y": p.y, "behind": rig.camera.is_position_behind(c)}
	return null


## How much of the frame is lit, sampled: a renderer that runs and draws
## nothing is the failure the render checks exist to catch (CLAUDE.md 10).
func lit_fraction() -> float:
	var img := get_viewport().get_texture().get_image()
	if img == null:
		return 0.0
	var bright := 0
	var total := 0
	for y in range(0, img.get_height(), 7):
		for x in range(0, img.get_width(), 7):
			total += 1
			if img.get_pixel(x, y).get_luminance() > 0.08:
				bright += 1
	return float(bright) / maxf(1.0, float(total))
