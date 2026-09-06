## The render proof for the itch track (CLAUDE.md 10), and the scene checks:
## `xvfb-run -a godot --path itch --rendering-driver opengl3 --script res://tests/scene_test.gd`
## Run with --resolution 390x844 for the phone frames the docs show.
## Loads the real main scene, walks the camera to every room and both puzzle
## stations the way main.gd does, waits for it to arrive, and writes a frame
## of each to docs/reference/itch_<name>.png, failing if a frame is black or
## if anything a tap needs is missing. Navigation only: nothing here solves
## a puzzle, the playthrough does that through real taps.
extends SceneTree

const OUT := "res://../docs/reference/"
var _n := 0
var main: Node


func ok(cond: bool, msg: String) -> void:
	if not cond:
		printerr("FAIL: " + msg)
		quit(1)
		await process_frame
		return
	_n += 1
	print("  ok  " + msg)


func _init() -> void:
	_run()


func _run() -> void:
	await process_frame
	var scene: PackedScene = load("res://scenes/main.tscn")
	main = scene.instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	ok(main.bodies.size() >= 120, "the raycast has %d bodies to stop on" % main.bodies.size())
	var kinds := {}
	for b in main.bodies:
		kinds[b.get_meta("kind")] = kinds.get(b.get_meta("kind"), 0) + 1
	ok(kinds.get("eye", 0) == 3 and kinds.get("pad", 0) == 6 and kinds.get("stone", 0) == 3 and kinds.get("stack", 0) == 4, "every prop a tap needs is there: %s" % str(kinds))
	ok(kinds.get("door", 0) == 4 and kinds.get("doorway", 0) == 5 and kinds.get("plaque", 0) == 11, "the shell's doors, doorways and plaques carry their kind")
	ok(main.view.slabs.size() == 4, "the four door slabs are bound")
	var lit := 0
	for m in MaterialLibrary.meshes(main.shell):
		for s in m.mesh.get_surface_count():
			var mat := m.get_surface_override_material(s)
			if mat and mat is StandardMaterial3D and (mat.albedo_texture or mat.emission_enabled or mat.albedo_color != Color.WHITE):
				lit += 1
	ok(lit >= 100, "%d shell surfaces wear a role material" % lit)
	# every room, instantly, then a frame each
	var names := ["forecourt", "gaze", "stack", "speech", "sixfold", "ancestor"]
	for r in 6:
		main.go_room(r, true)
		await _settle()
		await _shot("room%d_%s" % [r, names[r]])
	for st in ["gaze", "stack", "speech", "final"]:
		main.go_room(main.L.stations[st]["room"], true)
		main.go_station(st)
		await _settle()
		await _shot("station_" + st)
	print("ALL %d SCENE CHECKS PASSED" % _n)
	quit(0)


func _settle() -> void:
	for _i in 90:
		await process_frame
		if main.rig.arrived():
			break
	for _i in 3:
		await process_frame


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var bright := 0
	var step := 7
	var total := 0
	for y in range(0, img.get_height(), step):
		for x in range(0, img.get_width(), step):
			total += 1
			if img.get_pixel(x, y).get_luminance() > 0.08:
				bright += 1
	var frac := float(bright) / maxf(1.0, float(total))
	img.save_png(ProjectSettings.globalize_path(OUT + "itch_" + name + ".png"))
	ok(frac > 0.05, "%s: %.0f%% of the frame is lit" % [name, frac * 100.0])
