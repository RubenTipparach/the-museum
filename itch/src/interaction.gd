## The one raycast that resolves what the player touched (CLAUDE.md 4.1,
## ADR-4). The HUD, the puzzles and the playthrough all read this answer.
class_name Interaction
extends RefCounted


## What a tap at `pos` (viewport pixels) lands on. A hit closer than half a
## metre is something the camera stands in; a doorway closer than a metre and
## a bit is one the camera is passing through, not one being chosen.
static func resolve(camera: Camera3D, pos: Vector2, tuning: Dictionary) -> Dictionary:
	var exclude: Array[RID] = []
	for _i in 8:
		var hit := _cast(camera, pos, tuning, exclude)
		if hit.is_empty():
			return {}
		var near: float = tuning["nearDoorway"] if hit["kind"] == "doorway" else tuning["nearHit"]
		if hit["distance"] <= near:
			exclude.append(hit["rid"])
			continue
		return hit
	return {}


## The nearest few things under a point, nearest first, for the debug bridge.
static func hits(camera: Camera3D, pos: Vector2, tuning: Dictionary, count: int = 4) -> Array:
	var out: Array = []
	var exclude: Array[RID] = []
	for _i in count:
		var hit := _cast(camera, pos, tuning, exclude)
		if hit.is_empty():
			break
		out.append({"name": hit["body"].get_parent().name, "kind": hit["kind"], "d": snappedf(hit["distance"], 0.01)})
		exclude.append(hit["rid"])
	return out


static func _cast(camera: Camera3D, pos: Vector2, tuning: Dictionary, exclude: Array[RID]) -> Dictionary:
	var from := camera.project_ray_origin(pos)
	var to := from + camera.project_ray_normal(pos) * float(tuning["far"])
	var q := PhysicsRayQueryParameters3D.create(from, to)
	q.exclude = exclude
	var hit := camera.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return {}
	var body: Node3D = hit["collider"]
	return {"kind": body.get_meta("kind", "solid"), "body": body, "rid": hit["rid"], "position": hit["position"],
			"distance": from.distance_to(hit["position"]), "i": int(body.get_meta("i", -1)),
			"id": String(body.get_meta("id", "")), "peg": int(body.get_meta("peg", -1)), "centre": centre_of(body)}


## Where a thing actually is: the middle of the mesh it belongs to, because a
## shell part's own origin is the foot of the slab it was built from.
static func centre_of(body: Node3D) -> Vector3:
	var p := body.get_parent()
	if p is MeshInstance3D and p.mesh:
		return p.global_transform * p.mesh.get_aabb().get_center()
	return body.global_position
