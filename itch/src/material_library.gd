## Binds the material roles data/materials.json describes to their textures,
## once each, and dresses any imported model whose materials are named for
## roles. The one place a texture or a picture path is spelled (CLAUDE.md 4.1):
## the shell, the props and the HUD's chips all ask here.
class_name MaterialLibrary
extends RefCounted

const TEXTURE := "res://assets/textures/%s_%s.png"
const ART := "res://assets/art/%s.png"

static var _roles: Dictionary = {}
static var _art: Dictionary = {}


static func role(name: String) -> StandardMaterial3D:
	if _roles.has(name):
		return _roles[name]
	var table: Dictionary = DataFiles.materials()["roles"]
	assert(table.has(name), "no material role " + name)
	var def: Dictionary = table[name]
	var src: String = def.get("from", name)
	var maps: Array = def.get("maps", table.get(src, {}).get("maps", []))
	var m := StandardMaterial3D.new()
	m.resource_name = name
	m.roughness = def.get("roughness", 0.9)
	m.metallic = def.get("metallic", 0.0)
	if "albedo" in maps:
		m.albedo_texture = load(TEXTURE % [src, "albedo"])
	if "normal" in maps:
		m.normal_enabled = true
		m.normal_texture = load(TEXTURE % [src, "normal"])
		m.normal_scale = 0.8
	if "rough" in maps:
		m.roughness_texture = load(TEXTURE % [src, "rough"])
		m.roughness = 1.0
	if def.has("color"):
		m.albedo_color = Color(def["color"])
	if def.has("tint"):
		m.albedo_color = Color(def["tint"])
	if def.has("emission"):
		m.emission_enabled = true
		m.emission = Color(def["emission"])
		m.emission_energy_multiplier = def.get("emissionEnergy", 1.0)
		if def.get("emissionFromAlbedo", false) and m.albedo_texture:
			m.emission_texture = m.albedo_texture
	if def.has("alphaScissor"):
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
		m.alpha_scissor_threshold = def["alphaScissor"]
	if def.get("doubleSided", false):
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
	_roles[name] = m
	return m


## A surface that wears one picture from assets/art: the mat_decal role with
## that picture as its albedo. One material per picture, shared.
static func art(picture: String) -> StandardMaterial3D:
	if _art.has(picture):
		return _art[picture]
	var m: StandardMaterial3D = role("mat_decal").duplicate()
	m.resource_name = "art:" + picture
	m.albedo_texture = load(ART % picture)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.4
	_art[picture] = m
	return m


static func art_texture(picture: String) -> Texture2D:
	return load(ART % picture)


## Every surface of every mesh under `root` whose material is named for a
## role takes the library's material for it. The shell and the props both
## come through here, so a texture is bound in one place.
static func dress(root: Node) -> void:
	for mi in meshes(root):
		for s in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(s)
			if m and m.resource_name.begins_with("mat_"):
				mi.set_surface_override_material(s, role(m.resource_name))


## Put `picture` on a prop's decal surface, the face it turns to the room.
static func decal(prop: Node, picture: String) -> void:
	for mi in meshes(prop):
		for s in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(s)
			if m and m.resource_name == "mat_decal":
				mi.set_surface_override_material(s, art(picture))


## Every surface of every mesh under `prop` takes `material`.
static func cover(prop: Node, material: Material) -> void:
	for mi in meshes(prop):
		for s in mi.mesh.get_surface_count():
			mi.set_surface_override_material(s, material)


static func meshes(root: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	if root is MeshInstance3D and root.mesh:
		out.append(root)
	for c in root.get_children():
		out.append_array(meshes(c))
	return out
