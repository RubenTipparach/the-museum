## Runs when assets/exhibit/elmorian.glb is imported (named in its .import
## file). Gives every solid part of the shell a collision body made from its
## own mesh, so the one raycast in interaction.gd can stop on walls, doors and
## plaques, and names on that body what a tap on it means. Vines are leaves on
## cards and a tap goes through them, as it did in the prototype.
@tool
extends EditorScenePostImport


func _post_import(scene: Node) -> Object:
	_walk(scene, scene)
	return scene


func _walk(node: Node, owner: Node) -> void:
	if node is MeshInstance3D and node.mesh and not node.name.begins_with("vines_"):
		var body := StaticBody3D.new()
		body.name = node.name + "_col"
		var door := RegEx.create_from_string("^door_(\\d+)_slab$").search(node.name)
		if door:
			body.set_meta("kind", "door")
			body.set_meta("i", int(door.get_string(1)))
		elif node.name.begins_with("plaque_"):
			body.set_meta("kind", "plaque")
			body.set_meta("id", node.name.substr(7))
		else:
			body.set_meta("kind", "solid")
		var shape := CollisionShape3D.new()
		shape.name = "shape"
		shape.shape = node.mesh.create_trimesh_shape()
		node.add_child(body)
		body.owner = owner
		body.add_child(shape)
		shape.owner = owner
	for c in node.get_children():
		_walk(c, owner)
